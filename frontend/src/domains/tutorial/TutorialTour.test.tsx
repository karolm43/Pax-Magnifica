import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TUTORIAL_ATTR, TUTORIAL_TARGETS, type TutorialTargetId } from "./targets";
import { TOUR_STEPS } from "./tourSteps";
import { TutorialTour } from "./TutorialTour";
import { useTutorialStore } from "./tutorialStore";

const initial = useTutorialStore.getState();
const s = () => useTutorialStore.getState();
const step = (id: string) => TOUR_STEPS.find((t) => t.id === id)!;

/** A mounted, visible tutorial target (jsdom has no layout: the rect is stubbed). */
function mountTarget(id: TutorialTargetId, rect = { top: 100, left: 100, width: 200, height: 80 }) {
  const node = document.createElement("div");
  node.setAttribute(TUTORIAL_ATTR, id);
  node.getBoundingClientRect = () =>
    ({ ...rect, right: rect.left + rect.width, bottom: rect.top + rect.height, x: rect.left, y: rect.top }) as DOMRect;
  document.body.appendChild(node);
  return node;
}

function renderTour() {
  return render(
    <MemoryRouter initialEntries={["/game/g1"]}>
      <Routes>
        <Route path="/game/:mapid" element={<TutorialTour offerDelayMs={0} />} />
      </Routes>
    </MemoryRouter>,
  );
}

const calloutTitle = () => screen.getByRole("heading", { level: 3 }).textContent;

beforeEach(() => {
  localStorage.clear();
  useTutorialStore.setState(
    { ...initial, chapter: null, tourStep: null, tourOffered: false, tourSeenGames: [], tipsDisabled: false, seenTips: [], pulseTarget: null },
    true,
  );
});

afterEach(() => {
  document.querySelectorAll(`[${TUTORIAL_ATTR}]`).forEach((n) => n.remove());
  vi.useRealTimers();
});

describe("TutorialTour — offer", () => {
  it("offers the tour on the first visit and starts it", async () => {
    const user = userEvent.setup();
    mountTarget(TUTORIAL_TARGETS.map);
    renderTour();
    const offer = screen.getByRole("dialog", { name: "Screen tour" });
    expect(offer).toHaveTextContent("Take a quick tour of the screen?");
    await user.click(screen.getByRole("button", { name: "Start tour" }));
    expect(screen.queryByRole("dialog", { name: "Screen tour" })).toBeNull();
    expect(screen.getByRole("dialog", { name: step("map").title })).toBeInTheDocument();
  });

  it("Not now remembers the game; Skip all also disables tips", async () => {
    const user = userEvent.setup();
    const { unmount } = renderTour();
    await user.click(screen.getByRole("button", { name: "Not now" }));
    expect(screen.queryByRole("dialog", { name: "Screen tour" })).toBeNull();
    expect(s().tourSeenGames).toEqual(["g1"]);
    expect(s().tipsDisabled).toBe(false);
    unmount();

    useTutorialStore.setState({ tourSeenGames: [] });
    renderTour();
    await user.click(screen.getByRole("button", { name: "Skip all" }));
    expect(screen.queryByRole("dialog", { name: "Screen tour" })).toBeNull();
    expect(s().tipsDisabled).toBe(true);
  });

  it("does not offer again in a game already seen", () => {
    useTutorialStore.setState({ tourSeenGames: ["g1"] });
    renderTour();
    expect(screen.queryByRole("dialog", { name: "Screen tour" })).toBeNull();
  });
});

describe("TutorialTour — running", () => {
  beforeEach(() => {
    // Only three regions on screen: map, phase panel (no coach), hand.
    mountTarget(TUTORIAL_TARGETS.map, { top: 0, left: 0, width: 1024, height: 768 });
    mountTarget(TUTORIAL_TARGETS.phasePanel);
    mountTarget(TUTORIAL_TARGETS.hand, { top: 650, left: 200, width: 500, height: 100 });
  });

  it("walks Next / Back over visible steps only and finishes", async () => {
    const user = userEvent.setup();
    act(() => s().startTour());
    renderTour();
    expect(calloutTitle()).toBe(step("map").title);
    expect(screen.getByLabelText("Step 1 of 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Back/ })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /Next/ }));
    expect(calloutTitle()).toBe(step("phase").title); // coach missing -> phase panel fallback
    await user.click(screen.getByRole("button", { name: /Next/ }));
    // Economy, turn controls and strategy cards are not mounted: skipped.
    expect(calloutTitle()).toBe(step("hand").title);
    expect(screen.getByLabelText("Step 3 of 3")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Back/ }));
    expect(calloutTitle()).toBe(step("phase").title);
    await user.click(screen.getByRole("button", { name: /Next/ }));
    await user.click(screen.getByRole("button", { name: "Finish" }));
    expect(s().tourStep).toBeNull();
    expect(s().tourSeenGames).toEqual(["g1"]);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("keyboard: arrows move, Escape ends", async () => {
    const user = userEvent.setup();
    act(() => s().startTour());
    renderTour();
    await user.keyboard("{ArrowRight}");
    expect(calloutTitle()).toBe(step("phase").title);
    await user.keyboard("{ArrowLeft}");
    expect(calloutTitle()).toBe(step("map").title);
    await user.keyboard("{Escape}");
    expect(s().tourStep).toBeNull();
  });

  it("auto-skips a step whose region is not on screen", () => {
    act(() => s().setTourStep(TOUR_STEPS.findIndex((t) => t.id === "turn")));
    renderTour();
    expect(calloutTitle()).toBe(step("hand").title);
  });

  it("close and Skip all end the tour", async () => {
    const user = userEvent.setup();
    act(() => s().startTour());
    renderTour();
    await user.click(screen.getByRole("button", { name: "Close tour" }));
    expect(s().tourStep).toBeNull();

    act(() => s().startTour());
    await user.click(screen.getByRole("button", { name: "Skip all" }));
    expect(s().tourStep).toBeNull();
    expect(s().tipsDisabled).toBe(true);
  });

  it("ends when no step has a region on screen", () => {
    document.querySelectorAll(`[${TUTORIAL_ATTR}]`).forEach((n) => n.remove());
    act(() => s().startTour());
    renderTour();
    expect(s().tourStep).toBeNull();
  });
});

describe("TutorialTour — pulse", () => {
  it("rings the pulse target and clears it after a moment", () => {
    vi.useFakeTimers();
    useTutorialStore.setState({ tourSeenGames: ["g1"] });
    mountTarget(TUTORIAL_TARGETS.hand);
    renderTour();
    act(() => s().pulse(TUTORIAL_TARGETS.hand));
    expect(document.querySelector('[data-variant="pulse"]')).not.toBeNull();
    act(() => {
      vi.advanceTimersByTime(2600);
    });
    expect(s().pulseTarget).toBeNull();
    expect(document.querySelector('[data-variant="pulse"]')).toBeNull();
  });

  it("a click anywhere clears the pulse", async () => {
    useTutorialStore.setState({ tourSeenGames: ["g1"] });
    mountTarget(TUTORIAL_TARGETS.hand);
    renderTour();
    act(() => s().pulse(TUTORIAL_TARGETS.hand));
    await act(() => new Promise((r) => setTimeout(r, 5)));
    await userEvent.setup().click(document.body);
    expect(s().pulseTarget).toBeNull();
  });
});
