import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { getPlayerDisplayName } from "@/domains/game-shell/components/gameStatePlayers";
import type { PlayerData } from "@/entities/data/types";

/** Czy gracz jest „posadzony" (ma frakcję, nie jest talią/neutralny). */
function isSeated(player: PlayerData): boolean {
  if (!player.faction || player.faction === "neutral") return false;
  const name = getPlayerDisplayName(player, player.color).toLowerCase();
  return !name.endsWith(".deck") && !name.endsWith('.deck"');
}

/**
 * „Gracz pulpitu" — czyją rękę / kartę strategii / akcje pokazuje pulpit gracza
 * na mapie. Pulpit ma być widoczny CAŁY CZAS, także w fazach bez aktywnej tury
 * (status / agenda), gdzie backend nie wskazuje aktywnego gracza
 * (``active_player_id`` = null). Kolejność wyboru:
 *   1. aktywny gracz (``playerData[].active``) — normalny przypadek (strategia/akcja),
 *   2. mówca (``gameState.speaker`` to KOLOR) — sensowny „domyślny" gracz między turami,
 *   3. pierwszy posadzony gracz — ostatni fallback, by pulpit miał kogo pokazać.
 * Zwraca ``undefined`` tylko, gdy nie ma żadnego posadzonego gracza (pusty stan).
 */
export function useDeskPlayer(): PlayerData | undefined {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const players = gameData?.playerData ?? [];

  const active = players.find((p) => p.active);
  if (active) return active;

  const speaker = gameState?.speaker
    ? players.find((p) => p.color === gameState.speaker)
    : undefined;
  if (speaker && isSeated(speaker)) return speaker;

  return players.find(isSeated);
}
