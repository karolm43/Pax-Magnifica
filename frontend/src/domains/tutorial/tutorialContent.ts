/**
 * Treść okna „How to play” (samouczek). Ogólny przebieg gry i obsługa ekranu — bez liczb
 * z kart (te są w grze i w przeglądarce zasad). Teksty widoczne dla gracza po angielsku.
 * Każdy rozdział = krótkie akapity + punkty; `hint` to wyróżniona wskazówka „w tej grze”.
 */

export type ChapterId =
  | "goal"
  | "screen"
  | "round"
  | "strategy"
  | "action"
  | "tactical"
  | "strategic"
  | "combat"
  | "status"
  | "agenda"
  | "economy"
  | "cards"
  | "online";

export type Chapter = {
  id: ChapterId;
  title: string;
  intro: string;
  points: string[];
  hint?: string;
};

export const CHAPTERS: Chapter[] = [
  {
    id: "goal",
    title: "Goal of the game",
    intro:
      "You lead one of the great factions of the galaxy. The first player to reach the victory point goal (usually 10 points) wins.",
    points: [
      "Most points come from objectives: public objectives everyone can score, and secret objectives only you know.",
      "To score them you expand, build fleets, research technology, trade, negotiate and fight.",
      "Every faction plays differently — open your player area to read your faction abilities, leaders and starting technology.",
    ],
    hint: "The “What now?” section of the phase panel (top left) always tells you what to do next. Click “Learn more” in it to jump to the right chapter here.",
  },
  {
    id: "screen",
    title: "The screen",
    intro: "Everything happens on the galaxy map. Panels around it show your options.",
    points: [
      "Map: drag to pan, mouse wheel or + / - to zoom, 0 to fit. Click a system or planet to see what is there.",
      "Turn panel: your Strategy Card and turn buttons — Activate system, Pass, Component, Transaction, End turn.",
      "Hand (bottom): your action cards, promissory notes and secret objectives. Click a card to read it.",
      "Map toolbar: lenses (planet traits, tech skips, Space Cannon range), Event log, How to play and settings.",
      "Number keys 1–8 open each player's area; G shows objectives and points; ? lists all shortcuts.",
      "Chat (bottom left) talks to everyone or whispers to one player.",
      "“What now?” (in the phase panel, top left) tells you what to do at every moment; click its header to fold it to one line.",
    ],
    hint: "Choices about places — a planet, a system — are always made by clicking the highlighted targets on the map.",
  },
  {
    id: "round",
    title: "A game round",
    intro: "The game is played in rounds. Each round has four phases, always in this order:",
    points: [
      "1. Strategy phase — everyone picks a Strategy Card, which sets turn order.",
      "2. Action phase — players take turns, one action at a time, until everyone has passed.",
      "3. Status phase — score objectives, get new command tokens, ready your cards.",
      "4. Agenda phase — the Galactic Council votes on new laws. It only happens once someone has taken the Custodians token from Mecatol Rex.",
    ],
    hint: "The speaker (shown on the turn panel) picks first in the strategy phase and moves the game to the next phase when everyone is done.",
  },
  {
    id: "strategy",
    title: "Strategy phase",
    intro:
      "Starting with the speaker and going around the table, each player picks a Strategy Card from the Strategy Card table.",
    points: [
      "The number on the card is your initiative: lower numbers take their turns first in the action phase.",
      "Each card has a primary ability — a strong action only you can use — and a secondary ability other players may follow.",
      "Cards nobody picks gain a trade good, making them more attractive next round.",
      "With few players each player picks more than one card; the table shows how many.",
    ],
    hint: "Read each card's primary and secondary on the table before you pick.",
  },
  {
    id: "action",
    title: "Action phase",
    intro:
      "In initiative order, each player takes ONE action, then the next player goes. This repeats until everyone has passed.",
    points: [
      "Tactical action — activate a system to move ships into it, fight, invade planets and build units.",
      "Strategic action — use the primary ability of your Strategy Card. You must do this before you may pass.",
      "Component action — play an action card or use any ability marked “Action”.",
      "Pass — you take no more turns this round. Passed players can still follow secondaries and play some cards.",
    ],
    hint: "After your action press End turn to hand play to the next player.",
  },
  {
    id: "tactical",
    title: "Tactical action",
    intro:
      "Press Activate system and click a system: you place one command token from your tactic pool there. A system you already have a token in cannot be activated again this round.",
    points: [
      "Movement — drag ships that can reach the system (their move value) into it. Ships with capacity carry fighters and ground forces.",
      "Space Cannon — units with SPACE CANNON may shoot at the ships that arrived.",
      "Space combat — if another player has ships there, you fight.",
      "Invasion — bombard, then land ground forces on planets; win the ground combat to take control.",
      "Production — if you have a space dock or other PRODUCTION unit there, build new units.",
    ],
    hint: "The tactical panel on the map walks you through these steps one by one; press Next step to move on.",
  },
  {
    id: "strategic",
    title: "Strategy Cards & secondaries",
    intro:
      "When a player uses a Strategy Card's primary ability, every other player may follow its secondary ability.",
    points: [
      "Following a secondary usually costs one command token from your strategy pool.",
      "A window pops up asking each player in turn: follow or not.",
      "The active player cannot end their turn until everyone has decided.",
    ],
  },
  {
    id: "combat",
    title: "Combat",
    intro: "Combat is fought in rounds until only one side has units left (or one side retreats).",
    points: [
      "Each unit rolls one die (some roll more). Every result equal to or higher than its combat value is a hit.",
      "Each player assigns the hits they receive to their own units, which are destroyed.",
      "Units with Sustain Damage can take one hit without being destroyed; they are repaired in the status phase.",
      "Before space combat, Anti-Fighter Barrage can shoot down fighters.",
      "At the start of a round a player may announce a retreat to an adjacent system with no enemy ships where they have units or a planet.",
    ],
    hint: "All dice are rolled on the dice table on screen; the engine counts the hits.",
  },
  {
    id: "status",
    title: "Status phase",
    intro: "A short bookkeeping phase that the game mostly does for you.",
    points: [
      "Score objectives: at most one public and one secret objective you meet right now.",
      "A new public objective is revealed and everyone draws an action card.",
      "Command tokens are removed from the board; you gain new tokens and may rearrange all of them between your tactic, fleet and strategy pools.",
      "Exhausted planets and cards are readied, damaged units repaired, and Strategy Cards return to the table.",
    ],
    hint: "The status window shows only the decisions you need to make: what to score and where to put your tokens.",
  },
  {
    id: "agenda",
    title: "Agenda phase",
    intro: "The Galactic Council votes on two agendas each round, one after the other.",
    points: [
      "Starting next to the speaker, each player votes for an outcome by exhausting planets — each planet adds its influence as votes. You may abstain.",
      "Laws stay in play and change the rules; directives take effect once and are discarded.",
      "Some action cards are played during the vote (before or after the agenda is revealed).",
      "The speaker breaks ties.",
    ],
  },
  {
    id: "economy",
    title: "Resources, influence & tokens",
    intro: "Planets are your economy. Spending a planet exhausts it until the status phase.",
    points: [
      "Resources (left number) pay for units and technology.",
      "Influence (right number) pays for command tokens and gives votes in the Council.",
      "Trade goods can be spent as either resources or influence.",
      "Command tokens: tactic pool = activations, fleet pool = how many non-fighter ships may share a system, strategy pool = secondaries.",
      "Technology: research with the Technology Strategy Card. Colored prerequisites come from technologies you already own.",
    ],
    hint: "When you pay, the payment window offers “Auto” — or choose planets yourself.",
  },
  {
    id: "cards",
    title: "Cards in your hand",
    intro: "Your hand holds cards other players cannot see.",
    points: [
      "Action cards: drag a card from your hand onto the table to play it. Only cards you may play right now can be picked up.",
      "Some action cards are reactions — the game offers them at the right moment.",
      "Promissory notes: your faction's favors. Trade them in a transaction; others may play yours.",
      "Secret objectives: score them in the status phase (some during combat or the action phase).",
    ],
  },
  {
    id: "online",
    title: "Playing online",
    intro: "One player hosts the game on their computer; the others join with a link.",
    points: [
      "The host opens a network game from the main menu and sends each player their personal invite link.",
      "Every player sees only their own hand and secrets.",
      "Your game is saved automatically; the host can load it later with Load game.",
      "Bots can fill empty seats and play on their own.",
    ],
    hint: "Found a problem? Use Report bug — it saves a report with the current game state.",
  },
];

export function chapterById(id: ChapterId): Chapter {
  return CHAPTERS.find((c) => c.id === id) ?? CHAPTERS[0];
}
