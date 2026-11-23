import type { LoreKind } from "@/entities/lore/cardLore";
import { lookupCardLore } from "@/entities/lore/lookupLore";
import DetailsCardFlavor from "./DetailsCardFlavor";

/**
 * Flavour karty z pól lore (`entities/lore/cardLore.ts`) — zamyka kartę szczegółów kursywą,
 * jak `DetailsCard.Flavor` przy akcjach/reliktach. Brak tekstu = nic nie renderuje.
 */
export function CardLore({ kind, id }: { kind: LoreKind; id: string | null | undefined }) {
  const text = lookupCardLore(kind, id);
  return text ? <DetailsCardFlavor>{text}</DetailsCardFlavor> : null;
}
