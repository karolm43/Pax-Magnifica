import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { CoachContext } from "./coachHint";
import { BASE_COACH_CONTEXT } from "./coachContext.fixture";
import { MilestoneTips } from "./MilestoneTips";
import { useTutorialStore } from "./tutorialStore";

/** Someone else's turn, nothing happening: no tip is due. */
const base: CoachContext = { ...BASE_COACH_CONTEXT, myTurn: false };

let context: CoachContext | null = base;
vi.mock("./useCoachContext", () => ({ useCoachContext: () => context }));

const initial = useTutorialStore.getState();
const s = () => useTutorialStore.getState();

beforeEach(() => {
  localStorage.clear();
  context = base;
  useTutorialStore.setState(
    { ...initial, tourStep: null, tourOffered: false, tipsDisabled: false, seenTips: [], pulseTarget: null },
    true,
  );
});

const combatTip = () => screen.queryByRole("dialog", { name: "Your first battle" });

describe("MilestoneTips", () => {
  it("shows nothing when no moment is happening", () => {
    render(<MilestoneTips />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("shows the combat tip; Got it marks it seen for good", async () => {
    const user = userEvent.setup();
    context = { ...base, inCombat: true };
    const { rerender } = render(<MilestoneTips />);
    expect(combatTip()).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Got it" }));
    expect(s().seenTips).toEqual(["combat"]);
    expect(combatTip()).toBeNull();
    rerender(<MilestoneTips />);
    expect(combatTip()).toBeNull();
  });

  it("Show me pulses the tip's target", async () => {
    const user = userEvent.setup();
    context = { ...base, inCombat: true };
    render(<MilestoneTips />);
    await user.click(screen.getByRole("button", { name: "Show me" }));
    expect(s().pulseTarget).toBe("battle");
  });

  it("auto-dismisses once the moment is over", () => {
    context = { ...base, myTurn: true, phase: "strategy", myCardPicked: false };
    const { rerender } = render(<MilestoneTips />);
    expect(screen.getByRole("dialog", { name: "Your first Strategy Card" })).toBeInTheDocument();
    context = { ...base, myTurn: false, phase: "strategy", myCardPicked: true };
    rerender(<MilestoneTips />);
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(s().seenTips).toEqual(["strategy-pick"]);
  });

  it("is suppressed with tips disabled or during the tour, without marking seen", () => {
    context = { ...base, inCombat: true };
    act(() => useTutorialStore.setState({ tipsDisabled: true }));
    render(<MilestoneTips />);
    expect(combatTip()).toBeNull();
    act(() => useTutorialStore.setState({ tipsDisabled: false, tourOffered: true }));
    expect(combatTip()).toBeNull();
    act(() => useTutorialStore.setState({ tourOffered: false, tourStep: 2 }));
    expect(combatTip()).toBeNull();
    act(() => useTutorialStore.setState({ tourStep: null }));
    expect(combatTip()).toBeInTheDocument();
    expect(s().seenTips).toEqual([]);
  });
});
