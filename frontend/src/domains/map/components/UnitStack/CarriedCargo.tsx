import { SpriteUnitImage } from "@/shared/ui/Unit/components/SpriteUnitImage";
import { getUnitSprite } from "@/shared/ui/Unit/unitSprites";
import { getGenericUnitDataByAsyncId } from "@/entities/lookup/units";
import classes from "./CarriedCargo.module.css";

/** More icons than this per unit type would just be a blob again. */
const MAX_ICONS = 3;

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
        const sprite =
          getUnitSprite(colorAlias, `tkn_${unitId}`) ??
          getUnitSprite(colorAlias, unitId);
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
