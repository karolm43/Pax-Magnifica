import { useEffect, useMemo, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { useGameData } from "@/state/useGameContext";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useDeskPlayer } from "@/domains/game-shell/components/TurnControls/useDeskPlayer";
import { playerName, playerRgb } from "@/domains/strategy/PlayerChip";
import { filterPlayersWithAssignedFaction } from "@/entities/game/playerUtils";
import { PlayerBoard } from "./board/PlayerBoard";
import { briefingMode, commanderTips, vpRank } from "./commanderTips";
import { EmpireDock } from "./EmpireDock";
import { empireStats } from "./empireStats";
import { SeatSwitcher, TableBadges } from "./TableStrip";
import styles from "./PlayerTab.module.css";

/*
 * PLAYER TAB - one player with the COMPLETE information, always available: it does not depend on
 * anyone having the turn. Shows the desk player (``useDeskPlayer``) by default; the seat switcher
 * at the top shows anyone else.
 * [seat switcher] [table badges: VP & rank, speaker/tyrant, strategy cards, neighbors, breakthrough]
 * [player zone: leaders & mech | faction sheet | command sheet]
 * [below: briefing / opponent intel + empire | hand + army strength]
 * Turn actions live in the control panel on the map - not duplicated here.
 */

const PHASE_LABEL: [string, string][] = [
  ["strategy", "Strategy phase"],
  ["action", "Action phase"],
  ["status", "Status phase"],
  ["agenda", "Agenda phase"],
  ["setup", "Setup"],
  ["finished", "Game over"],
];

function phaseLabel(phase: string): string {
  return PHASE_LABEL.find(([key]) => phase.startsWith(key))?.[1] ?? "Game";
}

export function PlayerTab() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const gameData = useGameData();
  const { data: gameState } = useGameState(gameId);
  const desk = useDeskPlayer();
  const players = useMemo(
    () => filterPlayersWithAssignedFaction(gameData?.playerData ?? []),
    [gameData?.playerData],
  );
  const [chosenColor, setChosenColor] = useState<string | null>(null);
  // Zmiana gracza pulpitu (np. logowanie do miejsca) wraca do niego.
  useEffect(() => setChosenColor(null), [desk?.color]);
  const player = players.find((p) => p.color === chosenColor) ?? desk ?? players[0];

  const empire = useMemo(
    () => (player ? empireStats(player, gameData?.tiles) : undefined),
    [player, gameData?.tiles],
  );

  if (!player) {
    return (
      <div className={styles.empty}>
        <p>No players seated in this game yet.</p>
      </div>
    );
  }

  const phase = gameState?.phase ?? "unknown";
  const turnColor = gameState?.activeTurnPlayer ?? gameState?.activePlayer ?? null;
  const isDesk = desk != null && player.color === desk.color;
  const vpsToWin = gameData?.vpsToWin ?? 10;
  const idMap = gameData?.strategyCardIdMap;
  const objectives = [
    ...(gameData?.objectives?.stage1Objectives ?? []),
    ...(gameData?.objectives?.stage2Objectives ?? []),
    ...(gameData?.objectives?.customObjectives ?? []),
  ];
  const agenda = gameState?.agendaPhase ?? null;
  const tipContext = {
    player,
    players,
    objectives,
    vpsToWin,
    phase,
    isTurn: turnColor === player.color,
    agenda,
    empire,
    viewer: desk ?? null,
  };
  const tips = commanderTips(tipContext);
  const scouting = briefingMode(tipContext) === "scout";
  const voter = phase.startsWith("agenda") ? agenda?.voters[player.discordId] : undefined;
  const subtitle = [
    player.flexibleDisplayName && player.flexibleDisplayName !== playerName(player)
      ? player.flexibleDisplayName
      : null,
    phaseLabel(phase),
    `round ${gameData?.gameRound ?? "?"}`,
    player.isSpeaker ? "speaker" : null,
    player.controlType === "BOT" ? "bot" : null,
    isDesk || desk == null ? null : "viewing another player",
  ]
    .filter(Boolean)
    .join(" · ");
  const rank = vpRank(player, players);

  return (
    <div className={styles.layout} style={{ "--pc": playerRgb(player.color) } as CSSProperties}>
      <SeatSwitcher
        players={players}
        selectedColor={player.color}
        turnColor={turnColor}
        vpsToWin={vpsToWin}
        idMap={idMap}
        onSelect={(color) => setChosenColor(color === desk?.color ? null : color)}
      />
      <TableBadges
        player={player}
        subtitle={subtitle}
        vpsToWin={vpsToWin}
        rank={rank}
        votes={voter ? voter.available + voter.extra : null}
        scouting={scouting}
      />
      <PlayerBoard player={player} largestFleet={empire ? empire.largestFleet : null} />
      <EmpireDock
        gameId={gameId}
        player={player}
        own={isDesk}
        scouting={scouting}
        tips={tips}
        empire={empire}
      />
    </div>
  );
}

export default PlayerTab;
