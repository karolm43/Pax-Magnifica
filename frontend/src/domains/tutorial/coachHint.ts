/**
 * Podpowiedź „What now?” samouczka — CZYSTA funkcja stanu gry → krótka instrukcja dla gracza
 * przy ekranie. Bez reguł liczbowych: tylko „co teraz zrobić i gdzie kliknąć”. Szczegóły
 * (rozdział `chapter`) otwiera okno How to play (`tutorialContent.ts`).
 */
import type { ChapterId } from "./tutorialContent";

export type CoachContext = {
  phase: string;
  /** Czy trwa setup startowy (tajne cele, Custodians) przed pierwszą rundą. */
  setupPending: boolean;
  winner: boolean;
  /** Czyja tura (nazwa do wyświetlenia), null = brak gracza z turą. */
  turnName: string | null;
  /** Czy tura należy do gracza przy ekranie. */
  myTurn: boolean;
  /** Czy gracz z turą to bot. */
  turnIsBot: boolean;
  /** Czy gracz przy ekranie ma już kartę strategii w tej rundzie. */
  myCardPicked: boolean;
  /** Czy gracz przy ekranie zagrał już (wyczerpał) swoją kartę strategii. */
  myCardPlayed: boolean;
  passed: boolean;
  tookAction: boolean;
  activeSystem: string | null;
  tacticalStep: string | null;
  inCombat: boolean;
  /** Otwarte okno czasowe (np. secondary) i czy to gracz przy ekranie ma teraz zdecydować. */
  windowOpen: boolean;
  myDecision: boolean;
  isSpeaker: boolean;
  canAdvancePhase: boolean;
};

export type CoachHint = {
  title: string;
  lines: string[];
  chapter: ChapterId;
  /** Gracz przy ekranie ma coś do zrobienia (wyróżnienie panelu). */
  act: boolean;
};

const TACTICAL: Record<string, Omit<CoachHint, "act">> = {
  ACTIVATION: {
    title: "Tactical action: activate",
    lines: ["Click a system on the map to place a command token there and activate it."],
    chapter: "tactical",
  },
  MOVEMENT: {
    title: "Tactical action: move",
    lines: [
      "Click a glowing system (or drag ships) to stage a leg in your flight plan.",
      "Review capacity and fleet pool, then fly the plan and advance to the next step.",
    ],
    chapter: "tactical",
  },
  SPACE_CANNON: {
    title: "Tactical action: Space Cannon",
    lines: ["Units with SPACE CANNON in range may fire at the ships that moved in. Roll, or skip to the next step."],
    chapter: "combat",
  },
  SPACE_COMBAT: {
    title: "Tactical action: space combat",
    lines: ["If two players have ships in the active system, they fight. Follow the battle window round by round."],
    chapter: "combat",
  },
  INVASION: {
    title: "Tactical action: invasion",
    lines: [
      "Land ground forces from your ships on planets in the active system (click the planet).",
      "Defenders fight back in ground combat; win to take control of the planet.",
    ],
    chapter: "tactical",
  },
  PRODUCTION: {
    title: "Tactical action: production",
    lines: [
      "If you have units with PRODUCTION here (e.g. a space dock), you may build: press Open production.",
      "Pay with resources by exhausting planets. Then finish the action and press End turn.",
    ],
    chapter: "economy",
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
    };
  }
  if (c.isSpeaker && c.canAdvancePhase) {
    return {
      title: "Next phase",
      lines: ["Everyone is done. As the speaker, press Next phase."],
      chapter: "round",
      act: true,
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
    };
  }
  if (c.phase === "strategy") {
    return c.myCardPicked
      ? {
          title: "Strategy phase",
          lines: ["You have your Strategy Card. Wait for the others to pick theirs."],
          chapter: "strategy",
          act: false,
        }
      : {
          title: "Pick a Strategy Card",
          lines: [
            "Click a card on the Strategy Card table. Its number is your initiative: lower numbers act first.",
            "Each card has a strong primary ability (for you) and a secondary others may follow.",
          ],
          chapter: "strategy",
          act: true,
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
    };
  }
  return {
    title: "How to play",
    lines: ["Open How to play for a tour of the game, the screen and each phase."],
    chapter: "goal",
    act: false,
  };
}
