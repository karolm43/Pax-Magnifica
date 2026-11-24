import { SpriteUnitImage } from "@/shared/ui/Unit/components/SpriteUnitImage";
import { getUnitSprite } from "@/shared/ui/Unit/unitSprites";
import { getGenericUnitDataByAsyncId } from "@/entities/lookup/units";
import classes from "./CarriedCargo.module.css";

/** More icons than this per unit type would just be a blob again. */
const MAX_ICONS = 3;
/** A boarding group shows at most this many units (the token count is not drawn). */
const MAX_LOOSE = 4;

/**
 * Fighters / ground forces packed into a flying carrier (live move replay): a few small
 * overlapping icons on the hull, no counts (user decision: numbered badges in flight were a
 * blob). Shown only while the carrier flies; the units themselves unpack when it lands.
 */
export function CarriedCargo({
  cargo,
  colorAlias,
}: {
  cargo: { unitId: string; count: number }[];
  colorAlias: string;
}) {
  return (
    <div className={classes.cargo} aria-hidden="true">
      {cargo.map(({ unitId, count }) => {
        // The plain unit art: the `tkn_` sprite carries the round-rect token background.
        const sprite = getUnitSprite(colorAlias, unitId);
        if (!sprite) return null;
        const name = getGenericUnitDataByAsyncId(unitId)?.name ?? unitId;
        return (
          <span key={unitId} className={classes.group}>
            {Array.from({ length: Math.min(count, MAX_ICONS) }, (_, index) => (
              <span key={index} className={classes.icon}>
                <SpriteUnitImage sprite={sprite} alt={name} />
              </span>
            ))}
          </span>
        );
      })}
    </div>
  );
}

/**
 * Fighters / ground forces boarding or leaving a carrier (live move replay): a small loose
 * group of plain unit sprites instead of the numbered map token, so packing and unpacking
 * read as units, not as a badge sliding around.
 */
export function LooseCargo({
  unitId,
  count,
  colorAlias,
}: {
  unitId: string;
  count: number;
  colorAlias: string;
}) {
  const sprite = getUnitSprite(colorAlias, unitId);
  if (!sprite) return null;
  const name = getGenericUnitDataByAsyncId(unitId)?.name ?? unitId;
  return (
    <div className={classes.loose} aria-hidden="true">
      {Array.from({ length: Math.min(count, MAX_LOOSE) }, (_, index) => (
        <span key={index} className={classes.looseUnit}>
          <SpriteUnitImage sprite={sprite} alt={name} />
        </span>
      ))}
    </div>
  );
}
