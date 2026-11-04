import type { ImgHTMLAttributes } from "react";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { getTileById } from "@/entities/lookup/systems";
import { boardImageLoadingProps } from "@/shared/ui/imageLoading";

type TileProps = ImgHTMLAttributes<HTMLImageElement> & {
  systemId: string;
};

export const Tile = ({ systemId, alt, ...imgProps }: TileProps) => {
  const tile = getTileById(systemId);

  if (!tile) return null;

  return (
    <img
      {...boardImageLoadingProps}
      src={assetUrl(`/tiles/${tile.imagePath}`)}
      alt={alt || `System ${systemId}`}
      {...imgProps}
    />
  );
};
