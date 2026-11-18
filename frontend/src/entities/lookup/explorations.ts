import { explorations } from "@/entities/data/explorations";
import { withVariant } from "@/entities/lookup/variantData";
import { indexBy } from "@/entities/lookup/indexBy";
import type { Exploration } from "@/entities/data/types";

const explorationsMap = indexBy(explorations, (card) => card.id);

export function getExploration(explorationId: string): Exploration | undefined {
  return withVariant("explores", explorationId, explorationsMap.get(explorationId));
}
