import { describe, expect, it } from "vitest";
import { coachHint, type CoachContext } from "./coachHint";
import { CHAPTERS } from "./tutorialContent";

const base: CoachContext = {
  phase: "action",
  setupPending: false,
  winner: false,
  turnName: "The Federation of Sol",
  myTurn: true,
  turnIsBot: false,
  myCardPicked: true,
  myCardPlayed: false,
  passed: false,
  tookAction: false,
  activeSystem: null,
  tacticalStep: null,
  inCombat: false,
  windowOpen: false,
  myDecision: false,
  isSpeaker: false,
  canAdvancePhase: false,
};

const hint = (patch: Partial<CoachContext>) => coachHint({ ...base, ...patch });

describe("coachHint", () => {
  it("strategy phase: pick a card until you have one", () => {
    expect(hint({ phase: "strategy", myCardPicked: false }).title).toBe("Pick a Strategy Card");
    expect(hint({ phase: "strategy", myCardPicked: true }).act).toBe(false);
  });

  it("action phase: lists the actions and blocks Pass before the Strategy Card", () => {
    const h = hint({});
    expect(h.title).toBe("Your turn: take one action");
    expect(h.lines.join(" ")).toContain("only after you have played your Strategy Card");
    expect(hint({ myCardPlayed: true }).lines.join(" ")).toContain("Or Pass");
  });

  it("after an action or a pass: End turn", () => {
    expect(hint({ tookAction: true }).title).toBe("End your turn");
    expect(hint({ passed: true }).lines[0]).toContain("You passed");
  });

  it("tactical action follows the current step", () => {
    expect(hint({ activeSystem: "26", tacticalStep: "MOVEMENT" }).title).toContain("move");
    expect(hint({ activeSystem: "26", tacticalStep: "PRODUCTION" }).chapter).toBe("economy");
    expect(hint({ activeSystem: "26", tacticalStep: "INVASION" }).title).toContain("invasion");
  });

  it("someone else's turn: watch, with the bot named", () => {
    const h = hint({ myTurn: false, turnIsBot: true, turnName: "The Barony of Letnev" });
    expect(h.title).toBe("The Barony of Letnev (bot) is playing");
    expect(h.act).toBe(false);
  });

  it("decision window and combat take priority", () => {
    expect(hint({ myTurn: false, windowOpen: true, myDecision: true }).title).toBe(
      "Your decision",
    );
    expect(hint({ inCombat: true, activeSystem: "26" }).chapter).toBe("combat");
  });

  it("speaker is told to advance when everyone is done", () => {
    expect(hint({ myTurn: false, isSpeaker: true, canAdvancePhase: true }).title).toBe(
      "Next phase",
    );
  });

  it("status, agenda, setup and the end of the game", () => {
    expect(hint({ phase: "status.scoring" }).chapter).toBe("status");
    expect(hint({ phase: "agenda.voting", myTurn: false }).chapter).toBe("agenda");
    expect(hint({ setupPending: true }).title).toBe("Game setup");
    expect(hint({ winner: true }).title).toBe("The game is over");
  });

  it("every hint points at an existing chapter", () => {
    const ids = new Set(CHAPTERS.map((c) => c.id));
    const phases = ["strategy", "action", "status.scoring", "agenda.voting", "unknown"];
    const steps = ["ACTIVATION", "MOVEMENT", "SPACE_CANNON", "SPACE_COMBAT", "INVASION", "PRODUCTION"];
    for (const phase of phases) expect(ids.has(hint({ phase }).chapter)).toBe(true);
    for (const tacticalStep of steps) {
      expect(ids.has(hint({ activeSystem: "1", tacticalStep }).chapter)).toBe(true);
    }
  });

  it("each hint points at the screen region it talks about", () => {
    expect(hint({ phase: "strategy", myCardPicked: false }).targetId).toBe("strategy-cards");
    expect(hint({ activeSystem: "26", tacticalStep: "ACTIVATION" }).targetId).toBe("map");
    expect(hint({ activeSystem: "26", tacticalStep: "MOVEMENT" }).targetId).toBe("map");
    expect(hint({ activeSystem: "26", tacticalStep: "SPACE_CANNON" }).targetId).toBe("tactical-action");
    expect(hint({ activeSystem: "26", tacticalStep: "INVASION" }).targetId).toBe("tactical-action");
    expect(hint({ activeSystem: "26", tacticalStep: "SPACE_COMBAT" }).targetId).toBe("battle");
    expect(hint({ activeSystem: "26", tacticalStep: "PRODUCTION" }).targetId).toBe("tactical-action");
    expect(hint({ inCombat: true }).targetId).toBe("battle");
    expect(hint({ windowOpen: true, myDecision: true }).targetId).toBe("secondary-decision");
    expect(hint({ myTurn: false, isSpeaker: true, canAdvancePhase: true }).targetId).toBe("turn-controls");
    expect(hint({}).targetId).toBe("turn-controls");
    expect(hint({ tookAction: true }).targetId).toBe("turn-controls");
    expect(hint({ myTurn: false }).targetId).toBe("map");
    expect(hint({ phase: "status.scoring" }).targetId).toBe("phase-panel");
    expect(hint({ phase: "agenda.voting", myTurn: false }).targetId).toBe("phase-panel");
    expect(hint({ setupPending: true }).targetId).toBe("phase-panel");
    expect(hint({ winner: true }).targetId).toBeUndefined();
  });
});
