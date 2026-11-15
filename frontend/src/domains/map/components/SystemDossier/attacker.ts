import type { GameState, PlayerData } from "@/entities/data/types";
import type { Tile } from "@/entities/game/types";

/** Every faction with units anywhere in the system, space area first. */
export function factionsInSystem(tile: Tile): string[] {
  const zones = [tile, ...Object.values(tile.planets)];
  return [
    ...new Set(zones.flatMap((zone) => Object.keys(zone.unitsByFaction ?? {}))),
  ];
}

/**
 * Who is attacking in this system, when more than one faction is in it: the
 * active player if this is the system they activated, otherwise the only
 * faction present with a command token here. Null when the system is not
 * contested or the aggressor cannot be told.
 */
export function findAttacker(
  tile: Tile,
  gameState: GameState | null | undefined,
  players: PlayerData[],
): string | null {
  const present = factionsInSystem(tile);
  if (present.length < 2) return null;

  if (gameState?.activeSystem === tile.position) {
    const active = players.find(
      (player) => player.color === gameState.activePlayer,
    )?.faction;
    if (active && present.includes(active)) return active;
  }

  const activators = present.filter((faction) =>
    tile.commandCounters.includes(faction),
  );
  return activators.length === 1 ? activators[0] : null;
}
