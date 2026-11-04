import React from "react";
import cx from "clsx";
import { TokenSprite as TokenSpriteData } from "../tokenSprites";
import { sheetUrl } from "@/shared/assets/resolveAsset";
import "../tokenSprites.css";

type TokenSpriteProps = React.HTMLAttributes<HTMLDivElement> & {
  sprite: TokenSpriteData;
  alt: string;
};

export function TokenSprite({
  sprite,
  alt,
  className,
  style,
  ...props
}: TokenSpriteProps): React.ReactElement {
  return (
    <div
      role="img"
      aria-label={alt}
      {...props}
      style={{
        width: sprite.width,
        height: sprite.height,
        // Sprite sheet żetonów z LOKALNEGO backendu (`/static/tokens/sheets/...`),
        // bez CDN AsyncTI4 (R2.1).
        backgroundImage: `url("${sheetUrl("tokens", sprite.sheet)}")`,
        backgroundSize: `${sprite.sheetWidth}px ${sprite.sheetHeight}px`,
        backgroundPosition: `-${sprite.x}px -${sprite.y}px`,
        ...style,
      }}
      className={cx("token-sprite", className)}
    />
  );
}
