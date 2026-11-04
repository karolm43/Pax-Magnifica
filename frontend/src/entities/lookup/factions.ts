import { assetUrl } from "@/shared/assets/resolveAsset";
import type { FactionImageMap } from "@/entities/game/types";
import type { PlayerData } from "@/entities/data/types";

export function getFactionImage(
  faction: string,
  factionImage?: string,
  factionImageType?: string
): string | undefined {
  // Niegdyś ikona frakcji typu EMOJI szła z `emoji-cdn.mqrio.dev`, a typ DISCORD
  // z surowego URL profilu Discorda. Custodian Engine działa offline (R2.4): oba
  // zastępujemy LOKALNĄ grafiką frakcji z backendu. Gdy brak pliku w manifeście,
  // `assetUrl` zwraca lokalny placeholder — nigdy adres zewnętrzny.
  // Typy `factionImage*` są celowo ignorowane (zostają tylko dla zgodności danych).
  void factionImage;
  void factionImageType;
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
