import React from "react";
import { assetUrl } from "@/shared/assets/resolveAsset";

type BaseUnitImageProps = {
  urlColor: string;
  unitType: string;
  alt: string;
  className?: string;
};

export function BaseUnitImage(props: BaseUnitImageProps): React.ReactElement {
  const { urlColor, unitType, alt, className } = props;
  return (
    <img
      src={assetUrl(`/units/${urlColor}_${unitType}.png`)}
      alt={alt}
      className={className}
      decoding="async"
    />
  );
}
