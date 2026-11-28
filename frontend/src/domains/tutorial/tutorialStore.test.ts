import { beforeEach, describe, expect, it } from "vitest";
import { useTutorialStore } from "./tutorialStore";

const initial = useTutorialStore.getState();

beforeEach(() => {
  localStorage.clear();
  useTutorialStore.setState(
    { ...initial, tourStep: null, tourOffered: false, tourSeenGames: [], tipsDisabled: false, seenTips: [], pulseTarget: null },
    true,
  );
});

const s = () => useTutorialStore.getState();

describe("tutorialStore — tour", () => {
  it("offers the tour on the first visit to a game only", () => {
    s().offerTourIfFirstVisit("g1");
    expect(s().tourOffered).toBe(true);
    s().endTour("g1");
    expect(s().tourOffered).toBe(false);
    expect(JSON.parse(localStorage.getItem("tutorial:tour-seen") ?? "[]")).toEqual(["g1"]);
    s().offerTourIfFirstVisit("g1");
    expect(s().tourOffered).toBe(false);
    s().offerTourIfFirstVisit("g2");
    expect(s().tourOffered).toBe(true);
  });

  it("starts at step 0, moves, and ends", () => {
    s().startTour();
    expect(s().tourStep).toBe(0);
    s().setTourStep(3);
    expect(s().tourStep).toBe(3);
    s().setTourStep(-2);
    expect(s().tourStep).toBe(0);
    s().endTour();
    expect(s().tourStep).toBeNull();
  });

  it("Skip all disables the offer and the milestone tips persistently", () => {
    s().offerTourIfFirstVisit("g1");
    s().skipAll("g1");
    expect(s().tipsDisabled).toBe(true);
    expect(s().tourOffered).toBe(false);
    expect(localStorage.getItem("tutorial:tips-off")).toBe("1");
    s().offerTourIfFirstVisit("g2");
    expect(s().tourOffered).toBe(false);
  });

  it("Restart tour re-enables tips, forgets seen tips and starts the tour", () => {
    s().markTipSeen("combat");
    s().skipAll("g1");
    s().restartTour();
    expect(s().tipsDisabled).toBe(false);
    expect(s().seenTips).toEqual([]);
    expect(s().tourStep).toBe(0);
    expect(localStorage.getItem("tutorial:tips-off")).toBe("0");
  });
});

describe("tutorialStore — tips and pulse", () => {
  it("remembers each seen tip once", () => {
    s().markTipSeen("combat");
    s().markTipSeen("combat");
    expect(s().seenTips).toEqual(["combat"]);
    expect(JSON.parse(localStorage.getItem("tutorial:tips-seen") ?? "[]")).toEqual(["combat"]);
  });

  it("pulses and clears a target", () => {
    s().pulse("hand");
    expect(s().pulseTarget).toBe("hand");
    s().clearPulse();
    expect(s().pulseTarget).toBeNull();
  });
});
