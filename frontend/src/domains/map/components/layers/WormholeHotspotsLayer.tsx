import { useEffect } from "react";
import { useWormholeHoverStore } from "../../wormholeLinks";
import { forwardClickBelow } from "../forwardClickBelow";
import { getPrintedLinkPoints } from "./WormholeBlockedLayer";

/** Promień niewidocznego punktu nad nadrukiem (współrzędne kafelka). */
const HOTSPOT_RADIUS = 42;

/**
 * Niewidoczne punkty nad wormhole / egress NADRUKOWANYMI na kafelku: najechanie pokazuje
 * linie „dokąd prowadzi” (``WormholeLinkLayer``). Żetony wormhole/ingress mają to samo
 * w ``Token``. Klik przechodzi do systemu pod spodem.
 */
export function WormholeHotspotsLayer({
  systemId,
  position,
}: {
  systemId: string;
  position: string;
}) {
  const setHovered = useWormholeHoverStore((s) => s.setHovered);
  const clearHovered = useWormholeHoverStore((s) => s.clearHovered);
  useEffect(() => () => clearHovered(position), [position, clearHovered]);

  return (
    <>
      {getPrintedLinkPoints(systemId).map((point) => (
        <span
          key={point.kinds.join("-")}
          data-testid="wormhole-hotspot"
          aria-hidden="true"
          style={{
            position: "absolute",
            left: point.x - HOTSPOT_RADIUS,
            top: point.y - HOTSPOT_RADIUS,
            width: HOTSPOT_RADIUS * 2,
            height: HOTSPOT_RADIUS * 2,
            borderRadius: "50%",
            pointerEvents: "auto",
            zIndex: 50,
          }}
          onMouseEnter={() => setHovered({ position, kinds: point.kinds })}
          onMouseLeave={() => clearHovered(position)}
          onClick={forwardClickBelow}
        />
      ))}
    </>
  );
}
