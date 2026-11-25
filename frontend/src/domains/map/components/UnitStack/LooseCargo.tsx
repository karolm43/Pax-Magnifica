import { SpriteUnitImage } from "@/shared/ui/Unit/components/SpriteUnitImage";
import { getUnitSprite } from "@/shared/ui/Unit/unitSprites";
import { getGenericUnitDataByAsyncId } from "@/entities/lookup/units";
import classes from "./LooseCargo.module.css";

/** A boarding group shows at most this many units (the token count is not drawn). */
const MAX_LOOSE = 4;

/**
 * Fighters / ground forces boarding or leaving a carrier (live move replay): a small loose
 * group of plain unit sprites instead of the numbered map token, so packing and unpacking
 * read as units, not as a badge sliding around. They slip under the carrier's hull and
 * vanish; nothing of them is drawn while it flies (user decision).
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
