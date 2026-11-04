import { agendas } from "@/entities/data/agendas";
import { indexBy } from "@/entities/lookup/indexBy";

const agendasMap = indexBy(agendas, (card) => card.alias);

export const getAgenda = (alias: string) => agendasMap.get(alias);
