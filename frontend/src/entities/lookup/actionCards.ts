import { actionCards } from "@/entities/data/actionCards";
import { withVariant } from "@/entities/lookup/variantData";
import { indexBy } from "@/entities/lookup/indexBy";

const actionCardsMap = indexBy(actionCards, (card) => card.alias);

export const getActionCard = (alias: string) =>
  withVariant("action_cards", alias, actionCardsMap.get(alias));
