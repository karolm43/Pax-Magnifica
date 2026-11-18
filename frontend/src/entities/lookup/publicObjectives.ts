import { publicObjectives } from "@/entities/data/publicObjectives";
import { withVariant } from "@/entities/lookup/variantData";
import { indexBy } from "@/entities/lookup/indexBy";

const publicObjectivesMap = indexBy(publicObjectives, (card) => card.alias);

export const getPublicObjective = (alias: string) =>
  withVariant("public_objectives", alias, publicObjectivesMap.get(alias));
