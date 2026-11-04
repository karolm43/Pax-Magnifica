import { Tile } from "@/entities/game/types";
import { getAttachmentImagePath } from "@/entities/lookup/attachments";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { PlanetMarkersLayer } from "./PlanetMarkersLayer";

type Props = {
  systemId: string;
  mapTile: Tile;
};

export function AttachmentsLayer({ systemId, mapTile }: Props) {
  return (
    <PlanetMarkersLayer
      systemId={systemId}
      mapTile={mapTile}
      renderMarkers={(planetId, planet, x, y) =>
        (planet.attachments ?? []).flatMap((attachmentId, index) => {
          const imagePath = getAttachmentImagePath(attachmentId);
          if (!imagePath) return [];

          return [
            <img
              key={`${systemId}-${planetId}-attachment-${attachmentId}-${index}`}
              src={assetUrl(imagePath)}
              alt={`Attachment: ${attachmentId}`}
              title={attachmentId}
              style={{
                position: "absolute",
                left: `${x}px`,
                top: `${y + index * 30}px`,
                transform: "translate(-50%, -50%)",
                width: "70px",
                height: "auto",
                zIndex: `calc(var(--z-control-token) + ${index})`,
                filter: "drop-shadow(0 0 2px rgba(0, 0, 0, 0.8))",
              }}
            />,
          ];
        })
      }
    />
  );
}
