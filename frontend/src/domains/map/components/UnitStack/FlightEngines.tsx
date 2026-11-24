import type { CSSProperties } from "react";
import { ENGINES } from "@/shared/ui/Unit/engines";
import { getUnitSprite } from "@/shared/ui/Unit/unitSprites";
import classes from "./FlightEngines.module.css";

/** Ship art without a measurable sprite falls back to a typical hull size. */
const FALLBACK_SIZE = 70;
/** Stern distance from the sprite center, as a fraction of its size. */
const REAR = 0.36;

/**
 * Engine flames of a flying ship on the map (live move replay). Ship art faces north-west,
 * so the stern is south-east: the group is turned 45° and the flames trail along +x. It sits
 * inside the flying stack, so it banks, turns and shrinks into wormholes with the hull; it
 * lights up for the flight only (`--map-flight-duration`).
 */
export function FlightEngines({
  unitType,
  colorAlias,
  x,
  y,
  zIndex,
}: {
  unitType: string;
  colorAlias: string;
  x: number;
  y: number;
  zIndex: number;
}) {
  const nozzles = ENGINES[unitType];
  if (!nozzles) return null;
  const sprite = getUnitSprite(colorAlias, unitType);
  const size = sprite ? Math.min(sprite.width, sprite.height) : FALLBACK_SIZE;
  return (
    <span
      className={classes.engines}
      aria-hidden="true"
      style={{ left: x, top: y, zIndex } as CSSProperties}
    >
      {nozzles.offsets.map((offset, index) => (
        <span
          key={index}
          className={classes.flame}
          style={
            {
              left: size * REAR,
              top: offset * size - nozzles.height * 0.7,
              width: size * nozzles.length * 1.8,
              height: nozzles.height * 1.4,
              animationDelay: `${index * -0.4}s`,
            } as CSSProperties
          }
        />
      ))}
    </span>
  );
}
