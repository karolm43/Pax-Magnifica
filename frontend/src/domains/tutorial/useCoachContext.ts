import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useStrategyCards } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { useNetworkMe } from "@/domains/network/useNetworkMe";
import { getPlayerFactionDisplayName } from "@/entities/game/playerUtils";
import type { PlayerData } from "@/entities/data/types";
import type { CoachContext } from "./coachHint";

function seated(players: PlayerData[]): PlayerData[] {
  return players.filter((p) => p.faction && p.faction !== "neutral" && p.discordId);
}

/**
 * The player AT THE SCREEN: on the network my seat (token); locally and in test mode (a host
 * without a seat controls every player) the player whose turn it is, if human, otherwise the
 * first human at the table (solo vs bots).
 */
function viewer(
  players: PlayerData[],
  turn: PlayerData | undefined,
  me: { network?: boolean; host?: boolean; player_id?: string | null } | undefined,
): PlayerData | undefined {
  // Test mode behaves like local play - otherwise the coach said "Watch the map" on the player's turn.
  const testMode = me?.network === true && me.host === true && !me.player_id;
  if (me?.network && !testMode) return players.find((p) => p.discordId === me.player_id);
  if (turn && turn.controlType !== "BOT") return turn;
  return players.find((p) => p.controlType !== "BOT");
}

/**
 * Game state seen from the viewer's seat, reduced to what the tutorial needs ("What now?"
 * coach and milestone tips). Null while the game or its players are not loaded yet.
 */
export function useCoachContext(): CoachContext | null {
  const params = useParams<{ mapid: string }>();
  const { data: gameState } = useGameState(params.mapid ?? DEFAULT_GAME_ID);
  const gameData = useGameData();
  const { data: me } = useNetworkMe();
  const { data: cards } = useStrategyCards();
  if (!gameState) return null;
  const players = seated(gameData?.playerData ?? []);
  if (players.length === 0) return null;
  const turn = gameState.activeTurnPlayer
    ? players.find((p) => p.color === gameState.activeTurnPlayer)
    : undefined;
  const mine = viewer(players, turn, me);
  const myCards = (cards ?? []).filter((c) => mine && c.picked_by === mine.discordId);
  const window = gameState.pendingWindow;
  return {
    phase: gameState.phase ?? "unknown",
    setupPending: gameState.setup != null,
    winner: gameState.winnerId != null || gameState.phase === "finished",
    turnName: turn ? getPlayerFactionDisplayName(turn) : null,
    myTurn: turn != null && mine != null && turn.color === mine.color,
    turnIsBot: turn?.controlType === "BOT",
    myCardPicked: myCards.length > 0,
    myCardPlayed: myCards.some((c) => c.exhausted),
    passed: mine?.passed === true,
    tookAction: mine?.tookActionThisTurn === true,
    activeSystem: gameState.activeSystem ?? null,
    tacticalStep: gameState.tacticalStep ?? null,
    inCombat: gameState.activeCombat != null,
    windowOpen: window != null && !window.isComplete,
    myDecision: window != null && mine != null && window.currentResponderId === mine.discordId,
    isSpeaker: mine != null && gameState.speaker === mine.color,
    canAdvancePhase: gameState.canAdvancePhase === true,
  };
}
