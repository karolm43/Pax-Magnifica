import { useGameData } from "@/state/useGameContext";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { getTileById } from "@/entities/lookup/systems";
import {
  getPrintedLinkPoints,
  getWormholeCoordinates,
} from "@/entities/geometry/wormholePoints";

export { getPrintedLinkPoints };

type Props = {
  systemId: string;
};

export function WormholeBlockedLayer({ systemId }: Props) {
  const gameData = useGameData();
  const lawsInPlay = gameData?.lawsInPlay || [];

  const travelBanActive = lawsInPlay.some(
    (law) => law.id === "travel_ban" || law.id === "absol_travelban"
  );
  if (!travelBanActive) return null;
  const systemData = getTileById(systemId);
  if (!systemData) return null;

  const hasAlpha = systemData.wormholes?.includes("ALPHA") || false;
  const hasBeta = systemData.wormholes?.includes("BETA") || false;
  if (!hasAlpha && !hasBeta) return null;

  const reconstructionActive = lawsInPlay.some(
    (law) => law.id === "wormhole_recon" || law.id === "absol_recon"
  );
  const imageName = reconstructionActive
    ? "agenda_wormhole_blocked_half.png"
    : "agenda_wormhole_blocked.png";

  const coordinates = getWormholeCoordinates(
    systemId,
    systemData.shipPositionsType,
    hasAlpha,
    hasBeta,
    40
  );

  return (
    <>
      {coordinates.map((coord, index) => (
        <img
          key={`${systemId}-wh-blocked-${index}`}
          src={assetUrl(`/tokens/${imageName}`)}
          alt="Wormhole Blocked"
          style={{
            position: "absolute",
            left: `${coord.x}px`,
            top: `${coord.y}px`,
            pointerEvents: "none",
            zIndex: 2,
          }}
        />
      ))}
    </>
  );
}
