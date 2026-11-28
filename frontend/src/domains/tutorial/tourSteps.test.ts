import { describe, expect, it } from "vitest";
import { TUTORIAL_TARGETS, type TutorialTargetId } from "./targets";
import { TOUR_STEPS, nextAvailableStep, resolveStep, type TourStep } from "./tourSteps";
import { placeCallout, ringBox } from "./TutorialSpotlight";

const el = (name: string) => ({ name }) as unknown as HTMLElement;

function finder(present: TutorialTargetId[]) {
  return (id: TutorialTargetId) => (present.includes(id) ? el(id) : null);
}

const steps: TourStep[] = [
  { id: "a", target: TUTORIAL_TARGETS.map, title: "A", body: "" },
  { id: "b", target: [TUTORIAL_TARGETS.coach, TUTORIAL_TARGETS.phasePanel], title: "B", body: "" },
  { id: "c", target: TUTORIAL_TARGETS.hand, title: "C", body: "" },
  { id: "d", target: TUTORIAL_TARGETS.objectives, title: "D", body: "" },
];

describe("tour steps", () => {
  it("has 7-8 steps with unique ids and text", () => {
    expect(TOUR_STEPS.length).toBeGreaterThanOrEqual(7);
    expect(TOUR_STEPS.length).toBeLessThanOrEqual(8);
    expect(new Set(TOUR_STEPS.map((s) => s.id)).size).toBe(TOUR_STEPS.length);
    for (const s of TOUR_STEPS) {
      expect(s.title).not.toBe("");
      expect(s.body.length).toBeGreaterThan(40);
    }
  });

  it("resolveStep takes the first visible target in fallback order", () => {
    expect(resolveStep(steps[1], finder([TUTORIAL_TARGETS.phasePanel]))).toEqual(el("phase-panel"));
    expect(resolveStep(steps[1], finder([TUTORIAL_TARGETS.phasePanel, TUTORIAL_TARGETS.coach]))).toEqual(
      el("coach"),
    );
    expect(resolveStep(steps[2], finder([]))).toBeNull();
  });

  it("nextAvailableStep skips steps with no target on screen, both ways", () => {
    const find = finder([TUTORIAL_TARGETS.map, TUTORIAL_TARGETS.objectives]);
    expect(nextAvailableStep(steps, 0, 1, find)).toBe(3);
    expect(nextAvailableStep(steps, 3, -1, find)).toBe(0);
    expect(nextAvailableStep(steps, 3, 1, find)).toBeNull();
    expect(nextAvailableStep(steps, 0, -1, find)).toBeNull();
    // From before the start: the first available step.
    expect(nextAvailableStep(steps, -1, 1, finder([TUTORIAL_TARGETS.hand]))).toBe(2);
  });
});

describe("spotlight geometry", () => {
  const viewport = { width: 1000, height: 800 };

  it("pads the ring and clips it to the viewport; off-screen = null", () => {
    expect(ringBox({ top: 100, left: 100, width: 50, height: 50 }, viewport)).toEqual({
      top: 94,
      left: 94,
      width: 62,
      height: 62,
    });
    expect(ringBox({ top: 700, left: -100, width: 2000, height: 400 }, viewport)).toEqual({
      top: 694,
      left: 0,
      width: 1000,
      height: 106,
    });
    expect(ringBox({ top: 900, left: 0, width: 100, height: 100 }, viewport)).toBeNull();
  });

  it("places the callout below, above, beside, or inside a full-screen target", () => {
    const size = { width: 300, height: 150 };
    expect(placeCallout({ top: 50, left: 100, width: 100, height: 40 }, size, viewport).side).toBe("below");
    expect(placeCallout({ top: 650, left: 100, width: 100, height: 100 }, size, viewport).side).toBe("above");
    expect(placeCallout({ top: 0, left: 0, width: 200, height: 800 }, size, viewport).side).toBe("right");
    expect(placeCallout({ top: 0, left: 600, width: 400, height: 800 }, size, viewport).side).toBe("left");
    const inside = placeCallout({ top: 0, left: 0, width: 1000, height: 800 }, size, viewport);
    expect(inside.side).toBe("inside");
    expect(inside.top + size.height).toBeLessThanOrEqual(800);
  });

  it("clamps the callout horizontally to the viewport", () => {
    const p = placeCallout({ top: 10, left: 950, width: 40, height: 20 }, { width: 300, height: 100 }, viewport);
    expect(p.left + 300).toBeLessThanOrEqual(1000 - 12);
  });
});
