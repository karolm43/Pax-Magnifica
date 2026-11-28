import { describe, expect, it } from "vitest";
import type { CoachContext } from "./coachHint";
import { BASE_COACH_CONTEXT as base } from "./coachContext.fixture";
import { MILESTONE_TIPS, milestoneActive, pendingMilestone } from "./milestones";
import { TUTORIAL_TARGETS } from "./targets";
import type { MilestoneId } from "./tutorialStore";

const pending = (patch: Partial<CoachContext>, seen: MilestoneId[] = []) =>
  pendingMilestone({ ...base, ...patch }, seen);

describe("pendingMilestone", () => {
  it("strategy pick: only on my pick, until I have a card", () => {
    expect(pending({ phase: "strategy", myCardPicked: false })).toBe("strategy-pick");
    expect(pending({ phase: "strategy", myCardPicked: false, myTurn: false })).toBeNull();
    expect(pending({ phase: "strategy", myCardPicked: true, myTurn: false })).toBeNull();
  });

  it("tactical activation: my turn with no action yet, or activation/movement", () => {
    expect(pending({})).toBe("tactical-activation");
    expect(pending({ activeSystem: "26", tacticalStep: "ACTIVATION" })).toBe("tactical-activation");
    expect(pending({ activeSystem: "26", tacticalStep: "MOVEMENT" })).toBe("tactical-activation");
    expect(pending({ activeSystem: "26", tacticalStep: "INVASION" })).toBeNull();
    expect(pending({ tookAction: true })).toBeNull();
    expect(pending({ passed: true })).toBeNull();
    expect(pending({ myTurn: false })).toBeNull();
  });

  it("secondary: only when the open window waits for me", () => {
    expect(pending({ myTurn: false, windowOpen: true, myDecision: true })).toBe("secondary");
    expect(pending({ myTurn: false, windowOpen: true, myDecision: false })).toBeNull();
  });

  it("combat and production", () => {
    expect(pending({ myTurn: false, inCombat: true })).toBe("combat");
    expect(pending({ activeSystem: "26", tacticalStep: "PRODUCTION" })).toBe("production");
    expect(pending({ myTurn: false, activeSystem: "26", tacticalStep: "PRODUCTION" })).toBeNull();
  });

  it("the most urgent moment wins; seen tips are skipped", () => {
    expect(pending({ inCombat: true, activeSystem: "26", tacticalStep: "SPACE_COMBAT" })).toBe("combat");
    expect(pending({ inCombat: true, windowOpen: true, myDecision: true })).toBe("combat");
    expect(pending({ inCombat: true, windowOpen: true, myDecision: true }, ["combat"])).toBe("secondary");
    expect(pending({}, ["tactical-activation"])).toBeNull();
  });

  it("nothing during setup or after the game", () => {
    expect(pending({ setupPending: true, inCombat: true })).toBeNull();
    expect(pending({ winner: true })).toBeNull();
  });

  it("milestoneActive ignores what was seen", () => {
    expect(milestoneActive("combat", { ...base, inCombat: true })).toBe(true);
    expect(milestoneActive("combat", base)).toBe(false);
  });

  it("every tip has text and a known target", () => {
    const targets = new Set<string>(Object.values(TUTORIAL_TARGETS));
    for (const [id, tip] of Object.entries(MILESTONE_TIPS)) {
      expect(tip.id).toBe(id);
      expect(tip.title.length).toBeGreaterThan(0);
      expect(tip.lines.length).toBeGreaterThan(0);
      expect(targets.has(tip.targetId)).toBe(true);
    }
  });
});
