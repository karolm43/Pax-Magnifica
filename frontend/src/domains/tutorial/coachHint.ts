/**
 * The tutorial's "What now?" hint - a PURE function of game state -> a short instruction for the
 * player at the screen. No numeric rules: only "what to do now and where to click". Details
 * (the `chapter`) open in the How to play window (`tutorialContent.ts`); `targetId` names the
 * screen region the hint talks about ("Show me" pulses it).
 */
import type { ChapterId } from "./tutorialContent";
import { TUTORIAL_TARGETS, type TutorialTargetId } from "./targets";

export type CoachContext = {
  phase: string;
  /** Starting setup (secret objectives, Custodians) is in progress before the first round. */
  setupPending: boolean;
  winner: boolean;
  /** Whose turn it is (display name); null = no player has the turn. */
  turnName: string | null;
  /** The turn belongs to the player at the screen. */
  myTurn: boolean;
  /** The player whose turn it is is a bot. */
  turnIsBot: boolean;
  /** The player at the screen already has a Strategy Card this round. */
  myCardPicked: boolean;
  /** The player at the screen already played (exhausted) their Strategy Card. */
  myCardPlayed: boolean;
  passed: boolean;
  tookAction: boolean;
  activeSystem: string | null;
  tacticalStep: string | null;
  inCombat: boolean;
  /** An open timing window (e.g. a secondary) and whether the player at the screen decides now. */
  windowOpen: boolean;
  myDecision: boolean;
  isSpeaker: boolean;
  canAdvancePhase: boolean;
};

export type CoachHint = {
  title: string;
  lines: string[];
  chapter: ChapterId;
  /** The player at the screen has something to do (panel highlight). */
  act: boolean;
  /** Screen region the hint talks about; "Show me" pulses it. Absent = nothing to point at. */
  targetId?: TutorialTargetId;
};

const TACTICAL: Record<string, Omit<CoachHint, "act">> = {
  ACTIVATION: {
    title: "Tactical action: activate",
    lines: ["Click a system on the map to place a command token there and activate it."],
    chapter: "tactical",
    targetId: TUTORIAL_TARGETS.map,
  },
  MOVEMENT: {
    title: "Tactical action: move",
    lines: [
      "Click a glowing system (or drag ships) to stage a leg in your flight plan.",
      "Review capacity and fleet pool, then fly the plan and advance to the next step.",
    ],
    chapter: "tactical",
    targetId: TUTORIAL_TARGETS.map,
  },
  SPACE_CANNON: {
    title: "Tactical action: Space Cannon",
    lines: ["Units with SPACE CANNON in range may fire at the ships that moved in. Roll, or skip to the next step."],
    chapter: "combat",
    targetId: TUTORIAL_TARGETS.tacticalAction,
  },
  SPACE_COMBAT: {
    title: "Tactical action: space combat",
    lines: ["If two players have ships in the active system, they fight. Follow the battle window round by round."],
    chapter: "combat",
    targetId: TUTORIAL_TARGETS.battle,
  },
  INVASION: {
    title: "Tactical action: invasion",
    lines: [
      "Land ground forces from your ships on planets in the active system (click the planet).",
      "Defenders fight back in ground combat; win to take control of the planet.",
    ],
    chapter: "tactical",
    targetId: TUTORIAL_TARGETS.tacticalAction,
  },
  PRODUCTION: {
    title: "Tactical action: production",
    lines: [
      "If you have units with PRODUCTION here (e.g. a space dock), you may build: press Open production.",
      "Pay with resources by exhausting planets. Then finish the action and press End turn.",
    ],
    chapter: "economy",
    targetId: TUTORIAL_TARGETS.tacticalAction,
  },
};

export function coachHint(c: CoachContext): CoachHint {
  if (c.winner) {
    return {
      title: "The game is over",
      lines: ["Someone reached the victory point goal. Check the victory screen and the epilogue."],
      chapter: "goal",
      act: false,
    };
  }
  if (c.setupPending || c.phase.startsWith("setup")) {
    return {
      title: "Game setup",
      lines: [
        "Choose your starting secret objectives in the setup window.",
        "Check the map to see your starting fleet and nearby systems.",
      ],
      chapter: "goal",
      act: true,
      targetId: TUTORIAL_TARGETS.phasePanel,
    };
  }
  if (c.inCombat) {
    return {
      title: "Battle!",
      lines: [
        "Each round both sides roll one die per unit; a roll equal to or above the unit's combat value is a hit.",
        "Assign hits to your units (Sustain Damage lets a unit absorb one). At the start of a round you may announce a retreat.",
      ],
      chapter: "combat",
      act: true,
      targetId: TUTORIAL_TARGETS.battle,
    };
  }
  if (c.windowOpen && c.myDecision) {
    return {
      title: "Your decision",
      lines: [
        "Another player's card or action gives you a choice (for example, a Strategy Card secondary).",
        "Respond in the prompt on screen to continue.",
      ],
      chapter: "strategic",
      act: true,
      targetId: TUTORIAL_TARGETS.secondaryDecision,
    };
  }
  if (c.isSpeaker && c.canAdvancePhase) {
    return {
      title: "Next phase",
      lines: ["Everyone is done. As the speaker, press Next phase."],
      chapter: "round",
      act: true,
      targetId: TUTORIAL_TARGETS.turnControls,
    };
  }
  if (!c.myTurn && c.turnName && c.phase !== "status.scoring" && !c.phase.startsWith("agenda")) {
    return {
      title: c.turnIsBot ? `${c.turnName} (bot) is playing` : `${c.turnName}'s turn`,
      lines: [
        "Watch the map and the Event log to see what they do.",
        "Meanwhile, plan your next move: check objectives (G) and your cards.",
      ],
      chapter: "round",
      act: false,
      targetId: TUTORIAL_TARGETS.map,
    };
  }
  if (c.phase === "strategy") {
    return c.myCardPicked
      ? {
          title: "Strategy phase",
          lines: ["You have your Strategy Card. Wait for the others to pick theirs."],
          chapter: "strategy",
          act: false,
          targetId: TUTORIAL_TARGETS.strategyCards,
        }
      : {
          title: "Pick a Strategy Card",
          lines: [
            "Click a card on the Strategy Card table. Its number is your initiative: lower numbers act first.",
            "Each card has a strong primary ability (for you) and a secondary others may follow.",
          ],
          chapter: "strategy",
          act: true,
          targetId: TUTORIAL_TARGETS.strategyCards,
        };
  }
  if (c.phase === "action") {
    if (c.activeSystem) {
      const step = TACTICAL[c.tacticalStep ?? "MOVEMENT"] ?? TACTICAL.MOVEMENT;
      return { ...step, act: true };
    }
    if (c.windowOpen) {
      return {
        title: "Waiting for others",
        lines: ["Other players are deciding (e.g. whether to follow your secondary). Then press End turn."],
        chapter: "strategic",
        act: false,
        targetId: TUTORIAL_TARGETS.turnControls,
      };
    }
    if (c.passed || c.tookAction) {
      return {
        title: "End your turn",
        lines: [
          c.passed
            ? "You passed. Press End turn to hand over."
            : "Action done. Press End turn to pass play.",
        ],
        chapter: "action",
        act: true,
        targetId: TUTORIAL_TARGETS.turnControls,
      };
    }
    return {
      title: "Your turn: take one action",
      lines: [
        "Tactical: press Activate system and click a system to move, fight, invade and build.",
        "Strategic: play your Strategy Card from the turn panel.",
        "Component: drag an action card from your hand, or click Component for abilities.",
        c.myCardPlayed
          ? "Or Pass if you are done for this round."
          : "You can Pass only after you have played your Strategy Card.",
      ],
      chapter: "action",
      act: true,
      targetId: TUTORIAL_TARGETS.turnControls,
    };
  }
  if (c.phase.startsWith("status")) {
    return {
      title: "Status phase",
      lines: [
        "Score objectives you meet (at most one public and one secret) in the status window.",
        "Then place your new command tokens. The rest (new objective, action card, readying) is automatic.",
      ],
      chapter: "status",
      act: true,
      targetId: TUTORIAL_TARGETS.phasePanel,
    };
  }
  if (c.phase.startsWith("agenda")) {
    return {
      title: "Agenda phase",
      lines: [
        "The Galactic Council votes on two agendas. Exhaust planets to cast their influence as votes, or abstain.",
        "The winning outcome becomes law or takes effect at once.",
      ],
      chapter: "agenda",
      act: true,
      targetId: TUTORIAL_TARGETS.phasePanel,
    };
  }
  return {
    title: "How to play",
    lines: ["Open How to play for a tour of the game, the screen and each phase."],
    chapter: "goal",
    act: false,
  };
}
