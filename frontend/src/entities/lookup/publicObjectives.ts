import { publicObjectives } from "@/entities/data/publicObjectives";
import { indexBy } from "@/entities/lookup/indexBy";

const publicObjectivesMap = indexBy(publicObjectives, (card) => card.alias);

export const getPublicObjective = (alias: string) =>
  publicObjectivesMap.get(alias);
