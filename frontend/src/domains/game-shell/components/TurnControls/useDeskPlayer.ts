import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { useGameState } from "@/api/useGameState";
import { useGameData } from "@/state/useGameContext";
import { getPlayerDisplayName } from "@/domains/game-shell/components/gameStatePlayers";
import type { PlayerData } from "@/entities/data/types";
import { useNetworkMe } from "@/domains/network/useNetworkMe";

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
 *   1. gracz, którego jest TURA (``gameState.activeTurnPlayer`` to KOLOR) — czyja tura
 *      niezależnie od tego, czy już spasował (zagrał kartę + spasował, okno secondary
 *      otwarte — RULES.md 31.4/31.6); fallback na ``playerData[].active`` dla starych
 *      migawek bez tego pola,
 *   2. mówca (``gameState.speaker`` to KOLOR) — sensowny „domyślny" gracz między turami,
 *   3. pierwszy posadzony gracz — ostatni fallback, by pulpit miał kogo pokazać.
 * Zwraca ``undefined`` tylko, gdy nie ma żadnego posadzonego gracza (pusty stan).
 *
 * UWAGA: celowo NIE używamy wyłącznie ``playerData[].active`` — to pole gaśnie, gdy
 * aktywny gracz jest spasowany (``_effective_active_id`` w web-data), przez co pulpit
 * tury znikałby mimo że tura wciąż należy do tego gracza. ``activeTurnPlayer`` niesie
 * surową turę właśnie po to.
 */
export function useDeskPlayer(): PlayerData | undefined {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: gameState } = useGameState(gameId);
  const gameData = useGameData();
  const players = gameData?.playerData ?? [];
  const { data: me } = useNetworkMe();

  // Gra sieciowa (RULES.md 44.2): biurko to ZAWSZE moje miejsce (z tokenu), nie gracz z turą —
  // moja ręka i moje przyciski; poza moją turą kontrolki tury same się wyłączają.
  if (me?.network && me.player_id) {
    const mine = players.find((p) => p.discordId === me.player_id);
    if (mine) return mine;
  }

  const turnColor = gameState?.activeTurnPlayer;
  const turnPlayer = turnColor
    ? players.find((p) => p.color === turnColor)
    : undefined;
  if (turnPlayer) return turnPlayer;

  // Fallback: migawki bez ``activeTurnPlayer`` (stare) — po fladze ``active``.
  const active = players.find((p) => p.active);
  if (active) return active;

  const speaker = gameState?.speaker
    ? players.find((p) => p.color === gameState.speaker)
    : undefined;
  if (speaker && isSeated(speaker)) return speaker;

  return players.find(isSeated);
}
