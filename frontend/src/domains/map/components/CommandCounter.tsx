import React from "react";
import { assetUrl } from "@/shared/assets/resolveAsset";
import { useFactionTokenImage } from "@/hooks/useFactionTokenImage";

type CommandCounterProps = {
  colorAlias: string;
  faction?: string;
  style?: React.CSSProperties;
  type?: "command" | "fleet";
  /** Scale with the wrapper's width (set by `className`/`style`) instead of the asset's pixels. */
  fluid?: boolean;
  className?: string;
};

export const CommandCounter = ({
  colorAlias,
  faction,
  style,
  type = "command",
  fluid = false,
  className,
}: CommandCounterProps) => {
  const factionUrl = useFactionTokenImage(faction);
  return (
    <div style={style} className={className}>
      <div style={{ position: "relative" }}>
        <img
          src={assetUrl(`/command_token/${type}_${colorAlias}.png`)}
          alt={`${faction || type} ${type} token`}
          style={fluid ? { display: "block", width: "100%", height: "auto" } : undefined}
        />
        {faction && type === "command" && factionUrl && (
          <img
            src={factionUrl}
            alt={`${faction} faction`}
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -30%)",
              // 45 of the asset's 75 px: the same proportion when fluid.
              height: fluid ? "60%" : "45px",
              zIndex: 1,
            }}
          />
        )}
      </div>
    </div>
  );
};
