import { agendas } from "@/entities/data/agendas";
import { withVariant } from "@/entities/lookup/variantData";
import { indexBy } from "@/entities/lookup/indexBy";

const agendasMap = indexBy(agendas, (card) => card.alias);

export const getAgenda = (alias: string) =>
  withVariant("agendas", alias, agendasMap.get(alias));
