import type { CSSProperties } from "react";
import { ENGINES } from "@/shared/ui/Unit/engines";
import { getUnitSprite } from "@/shared/ui/Unit/unitSprites";
import classes from "./FlightEngines.module.css";

/** Ship art without a measurable sprite falls back to a typical hull size. */
const FALLBACK_SIZE = 70;
/** Stern distance from the sprite center, as a fraction of its size. */
const REAR = 0.34;

/** Elements the flight animation throttles with the ship's thrust curve. */
export const THRUST_SELECTOR = "[data-thrust]";
/** Force fields the flight animation fades in and out (`buildPathKeyframes` `shield` / `drive`). */
export const SHIELD_SELECTOR = "[data-shield]";
export const DRIVE_SELECTOR = "[data-drive]";

/**
 * Engine flames and ion wake of a flying ship on the map (live move replay). Ship art faces
 * north-west, so the stern is south-east: the group is turned 45° and the flames trail along
 * +x. It sits inside the flying stack, so it banks, turns and shrinks into wormholes with
 * the hull.
 *
 * `throttled` (routed live flights): each nozzle and the wake follow the ship's thrust curve
 * (`useMapFlightAnimation` animates `[data-thrust]`): a flare at launch, a burn that follows
 * its speed, dying down as it brakes. Otherwise (history replays) a fixed CSS burn lights
 * them for the flight (`--map-flight-duration`).
 *
 * `deflectors` (route crosses an asteroid field): the Antimass Deflector field glows around the
 * hull while it is inside. `gravityDrive`: a gravity well wraps the ship for the whole flight.
 * Both are routed-flight only (`throttled`).
 */
export function FlightEngines({
  unitType,
  colorAlias,
  x,
  y,
  zIndex,
  throttled = false,
  deflectors = false,
  gravityDrive = false,
}: {
  unitType: string;
  colorAlias: string;
  x: number;
  y: number;
  zIndex: number;
  throttled?: boolean;
  deflectors?: boolean;
  gravityDrive?: boolean;
}) {
  const nozzles = ENGINES[unitType];
  if (!nozzles) return null;
  const sprite = getUnitSprite(colorAlias, unitType);
  const size = sprite ? Math.min(sprite.width, sprite.height) : FALLBACK_SIZE;
  const field = (diameter: number) =>
    ({ left: x, top: y, width: diameter, height: diameter, zIndex }) as CSSProperties;
  const thrust = throttled ? { "data-thrust": "" } : {};
  const spread = Math.max(...nozzles.offsets) - Math.min(...nozzles.offsets);
  const wakeHeight = spread * size + nozzles.height * 2.6;
  return (
    <>
      {throttled && gravityDrive && (
        <span
          data-drive=""
          className={classes.drive}
          aria-hidden="true"
          style={field(size * 2.3)}
        />
      )}
      {throttled && deflectors && (
        <span
          data-shield=""
          className={classes.shield}
          aria-hidden="true"
          style={field(size * 1.55)}
        />
      )}
    <span
      className={`${classes.engines} ${throttled ? classes.throttled : ""}`}
      aria-hidden="true"
      style={{ left: x, top: y, zIndex } as CSSProperties}
    >
      <span
        {...thrust}
        className={classes.wake}
        style={{
          left: size * REAR,
          top: -wakeHeight / 2,
          width: size * 2.4,
          height: wakeHeight,
        }}
      />
      {nozzles.offsets.map((offset, index) => (
        <span
          key={index}
          {...thrust}
          className={classes.nozzle}
          style={{
            left: size * REAR,
            top: offset * size - nozzles.height,
            width: size * nozzles.length * 2.6,
            height: nozzles.height * 2,
          }}
        >
          <span
            className={classes.flame}
            style={{ animationDelay: `${index * -0.17}s` }}
          />
        </span>
      ))}
    </span>
    </>
  );
}
