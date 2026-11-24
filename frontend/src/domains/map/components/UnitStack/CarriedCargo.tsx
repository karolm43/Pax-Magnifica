import { SpriteUnitImage } from "@/shared/ui/Unit/components/SpriteUnitImage";
import { getUnitSprite } from "@/shared/ui/Unit/unitSprites";
import { getGenericUnitDataByAsyncId } from "@/entities/lookup/units";
import classes from "./CarriedCargo.module.css";

/**
 * Ground forces riding inside a flying ship (live move replay): mini sprites with counts
 * pinned to the hull, so transported infantry/mechs visibly travel with their carrier.
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
          getUnitSprite(colorAlias, unitId === "gf" ? "tkn_gf" : unitId) ??
          getUnitSprite(colorAlias, unitId);
        const name = getGenericUnitDataByAsyncId(unitId)?.name ?? unitId;
        return (
          <span key={unitId} className={classes.item}>
            {sprite && <SpriteUnitImage sprite={sprite} alt={name} />}
            <b className={classes.count}>{count}</b>
          </span>
        );
      })}
    </div>
  );
}
