/**
 * Contextual micro-helps (tutorial Layer 4): the short texts behind the small `?` buttons in
 * the HUD. Conceptual only - no numbers from cards (those live in the game data and the rules
 * browser). Each help may link to a chapter of the How to play guide.
 */
import type { ChapterId } from "./tutorialContent";

export type MicroHelp = {
  /** Short topic name, used in the button's accessible name ("Help: <topic>"). */
  topic: string;
  title: string;
  /** 2-5 short lines, rendered as bullets. */
  lines: string[];
  /** How to play chapter opened by "Learn more". */
  chapter?: ChapterId;
};

export const MICRO_HELPS = {
  commandPools: {
    topic: "Command tokens",
    title: "Command tokens (T / F / S)",
    lines: [
      "Tactic pool (T): spend one to activate a system for a tactical action; some abilities also spend them.",
      "Fleet pool (F): limits how many non-fighter ships you may have in each system. These tokens are not spent.",
      "Strategy pool (S): spend one to follow the secondary ability of another player's Strategy Card.",
      "In the status phase you gain two command tokens and may redistribute the tokens on your command sheet.",
    ],
    chapter: "economy",
  },
  tradeGoods: {
    topic: "Trade goods and commodities",
    title: "Trade goods & commodities",
    lines: [
      "Trade goods can be spent as resources or as influence.",
      "Commodities have no value to you: trade them to another player and they become that player's trade goods.",
      "Your commodity value (the number after the slash) is the most commodities you can hold.",
    ],
    chapter: "economy",
  },
  tacticalAction: {
    topic: "Tactical action",
    title: "Tactical action",
    lines: [
      "Activation: a command token from your tactic pool is placed in the system.",
      "Then the steps run in order: movement, Space Cannon offense, space combat, invasion, production. Steps with nothing to resolve are skipped.",
      "The main button resolves the current step and moves on to the next one.",
      "Undo activation takes the token back while nothing has moved yet.",
      "End action now skips the remaining steps, unless something is still unresolved (e.g. a mandatory space combat).",
    ],
    chapter: "tactical",
  },
  secondary: {
    topic: "Strategy Card secondary",
    title: "Secondary ability",
    lines: [
      "When a player resolves a Strategy Card's primary ability, every other player may resolve its secondary ability.",
      "Following usually costs one command token from your strategy pool; the cost line below shows what this one costs you.",
      "You may decline: choose Don't follow and nothing is spent.",
      "Players decide in turn order, starting with the player to the left of the active player.",
    ],
    chapter: "strategic",
  },
  battle: {
    topic: "Combat",
    title: "How combat works",
    lines: [
      "Combat is fought in rounds until only one side has units left, or one side retreats.",
      "At the start of each round a player may announce a retreat.",
      "Each unit rolls its combat dice; every result equal to or higher than its combat value is a hit.",
      "Each player assigns the hits they receive to their own units, which are destroyed.",
      "A unit with Sustain Damage may take one hit without being destroyed.",
    ],
    chapter: "combat",
  },
} as const satisfies Record<string, MicroHelp>;

export type MicroHelpId = keyof typeof MICRO_HELPS;
