import { assetUrl } from "@/shared/assets/resolveAsset";
import classes from "../MapTile.module.css";

type Props = {
  show: boolean;
  width: number;
  height: number;
};

export function AnomalyOverlay({ show, width, height }: Props) {
  if (!show) return null;
  return (
    <img
      src={assetUrl("/emojis/tiles/Anomaly.png")}
      alt="Anomaly"
      className={classes.anomalyOverlay}
      style={{ width, height }}
    />
  );
}
