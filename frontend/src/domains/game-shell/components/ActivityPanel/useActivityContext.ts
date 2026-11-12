import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { DEFAULT_GAME_ID } from "@/config";
import { usePlayerData } from "@/api/usePlayerData";
import type { ActivityPlayer } from "@/api/useBoardEditor";
import { useGameData } from "@/state/useGameContext";
import { getPlanetsByTileId } from "@/entities/lookup/planets";
import type { PlayerDataResponse } from "@/entities/data/types";
import { resolveSystemName } from "../GameEventPanel/eventFormatting";
import type { ActivityContext } from "./describeActivity";

const selectTilePositions = (data: PlayerDataResponse) => data.tilePositions;

/**
 * Kontekst do opisu wpisów feedu (nazwy systemów, podpowiedzi planet, mapa kart strategii).
 * Wspólny dla panelu Activity i wyskakujących powiadomień (ActivityToasts).
 */
export function useActivityContext(
  players: Record<string, ActivityPlayer> | undefined,
): ActivityContext {
  const params = useParams<{ mapid: string }>();
  // Trasa `/game` nie ma `mapid` - pusty identyfikator dawał 404 i nierozwiązane nazwy systemów.
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: tilePositions } = usePlayerData(gameId, {
    select: selectTilePositions,
  });
  const gameData = useGameData();
  return useMemo(() => {
    const positionToSystemId: Record<string, string> = {};
    for (const entry of tilePositions ?? []) {
      const [pos, systemId] = entry.split(":");
      if (pos && systemId) positionToSystemId[pos] = systemId;
    }
    return {
      players: players ?? {},
      systemName: (pos) => resolveSystemName(pos, positionToSystemId),
      systemHint: (pos) => {
        const systemId = positionToSystemId[pos];
        if (!systemId) return "";
        const planets = getPlanetsByTileId(systemId.replace(/^0+/, "") || systemId);
        if (planets.length === 0) return "No planets";
        return planets
          .map((p) => `${p.name}: ${p.resources} resources / ${p.influence} influence`)
          .join("\n");
      },
      strategyCardIdMap: gameData?.strategyCardIdMap,
    };
  }, [tilePositions, players, gameData?.strategyCardIdMap]);
}
