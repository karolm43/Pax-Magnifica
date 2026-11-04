import { assetUrl } from "@/shared/assets/resolveAsset";
import type { FactionImageMap } from "@/entities/game/types";
import type { PlayerData } from "@/entities/data/types";

export function getFactionImage(
  faction: string,
  factionImage?: string,
  factionImageType?: string
): string | undefined {
  if (factionImageType === "EMOJI") {
    return `https://emoji-cdn.mqrio.dev/${factionImage}?style=twitter`;
  }
  if (factionImageType === "DISCORD") return factionImage;
  return assetUrl(`/factions/${faction}.png`);
}

export function buildFactionImageMap(
  playerData: PlayerData[]
): FactionImageMap {
  return Object.fromEntries(
    playerData.map((player) => [
      player.faction,
      {
        image: player.factionImage ?? "",
        type: player.factionImageType ?? "",
      },
    ]),
  );
}
