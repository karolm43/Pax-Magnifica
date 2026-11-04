import { assetUrl } from "@/shared/assets/resolveAsset";

type LawOverlayProps = {
  tokenPath: string;
  alt: string;
};

export function LawOverlay({ tokenPath, alt }: LawOverlayProps) {
  return (
    <img
      src={assetUrl(tokenPath)}
      alt={alt}
      style={{
        position: "absolute",
        top: "0",
        left: "0",
      }}
    />
  );
}
