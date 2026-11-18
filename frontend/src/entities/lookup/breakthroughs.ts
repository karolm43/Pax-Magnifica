import { breakthroughs } from "@/entities/data/breakthroughs";
import { withVariant } from "@/entities/lookup/variantData";
import { indexBy } from "@/entities/lookup/indexBy";
import type { Breakthrough } from "@/entities/data/types";

const breakthroughMap = indexBy(breakthroughs, (b) => b.alias);

export function getBreakthroughData(id: string): Breakthrough | undefined {
  return withVariant("breakthroughs", id, breakthroughMap.get(id));
}
