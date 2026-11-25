import { primaryAction, lockReason, stepPrompt, stepStatuses, type StepContext } from "./tacticalSteps";

const ctx = (over: Partial<StepContext> = {}): StepContext => ({
  system: "Mecatol Rex",
  moved: false,
  stagedShips: 0,
  stagedCargo: 0,
  stagedSystems: 0,
  flightBlocker: null,
  windowType: null,
  inCombat: false,
  combatOwed: false,
  invasionOpen: false,
  invasionResolved: false,
  ...over,
});

describe("step statuses", () => {
  it("steps the window never saw between seen ones were skipped", () => {
    const s = stepStatuses("INVASION", ["MOVEMENT", "INVASION"]);
    expect(s).toEqual({
      MOVEMENT: "done",
      SPACE_CANNON: "skipped",
      SPACE_COMBAT: "skipped",
      INVASION: "active",
      PRODUCTION: "upcoming",
    });
  });

  it("opened mid-action: earlier steps count as done", () => {
    const s = stepStatuses("SPACE_COMBAT", ["SPACE_COMBAT"]);
    expect(s.MOVEMENT).toBe("done");
    expect(s.SPACE_CANNON).toBe("done");
    expect(s.SPACE_COMBAT).toBe("active");
  });
});

describe("primary action", () => {
  it("a staged flight plan flies first", () => {
    const action = primaryAction("MOVEMENT", ctx({ stagedShips: 3, stagedSystems: 2 }));
    expect(action).toEqual({ kind: "fly", label: "Fly 3 ships from 2 systems", disabled: null });
  });

  it("a plan that cannot fly says why", () => {
    const action = primaryAction(
      "MOVEMENT",
      ctx({ stagedShips: 1, stagedSystems: 1, flightBlocker: "Gravity Drive twice" }),
    );
    expect(action.disabled).toBe("Gravity Drive twice");
  });

  it("nothing moved: the next step is explicit about it", () => {
    expect(primaryAction("MOVEMENT", ctx()).label).toBe("No movement - next step");
    expect(primaryAction("MOVEMENT", ctx({ moved: true })).label).toBe("Next step");
  });

  it("during a combat the window leads back to the battle", () => {
    expect(primaryAction("SPACE_COMBAT", ctx({ inCombat: true })).kind).toBe("battle");
  });

  it("a mandatory combat that did not start yet is started by hand", () => {
    const action = primaryAction("SPACE_COMBAT", ctx({ combatOwed: true }));
    expect(action).toMatchObject({ kind: "startCombat", disabled: null });
  });

  it("the last step finishes the action; open windows lock it with a how-to", () => {
    expect(primaryAction("PRODUCTION", ctx()).kind).toBe("finish");
    const locked = primaryAction("PRODUCTION", ctx({ windowType: "FLEET_POOL" }));
    expect(locked.disabled).toMatch(/fleet pool window/);
  });

  it("an open invasion blocks leaving the step", () => {
    expect(lockReason(ctx({ invasionOpen: true }), "INVASION")).toMatch(/finish or skip/);
  });
});

describe("step prompt", () => {
  it("tells a first-time player where to click", () => {
    expect(stepPrompt("MOVEMENT", ctx())).toMatch(/Click a glowing system/);
    expect(stepPrompt("SPACE_COMBAT", ctx({ combatOwed: true }))).toMatch(/must be fought/);
  });
});
