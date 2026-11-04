import type { CSSProperties } from "react";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { TokenSprite } from "@/shared/ui/Token/components/TokenSprite";
import type { TokenSprite as TokenSpriteData } from "@/shared/ui/Token/tokenSprites";

type Props = {
  sprite: TokenSpriteData | undefined;
  imagePath: string;
  alt: string;
  style: CSSProperties;
};

/** Renders a token-sheet sprite when one exists, else the standalone image. */
export function PositionedSprite({ sprite, imagePath, alt, style }: Props) {
  if (sprite) return <TokenSprite sprite={sprite} alt={alt} style={style} />;
  return <img src={assetUrl(imagePath)} alt={alt} style={style} />;
}
