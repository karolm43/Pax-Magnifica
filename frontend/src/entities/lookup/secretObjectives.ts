import { secretObjectives } from "@/entities/data/secretObjectives";
import { withVariant } from "@/entities/lookup/variantData";
import { indexBy } from "@/entities/lookup/indexBy";
import type { SecretObjective } from "@/entities/data/types";

const secretObjectivesMap = indexBy(secretObjectives, (obj) => obj.alias);

export function getSecretObjectiveData(
  objectiveAlias: string
): SecretObjective | undefined {
  return withVariant(
    "secret_objectives",
    objectiveAlias,
    secretObjectivesMap.get(objectiveAlias),
  );
}
