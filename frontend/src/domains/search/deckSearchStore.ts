import { create } from "zustand";
import type { PileTab } from "@/domains/cards/model/deckPiles";

/**
 * Prośba z wyszukiwarki planszy: „otwórz tę talię (na tej zakładce)". Rewersy talii w
 * zakładce General subskrybują sklep i same otwierają swoje okno; `nonce` pozwala
 * ponowić prośbę o tę samą talię.
 */
export type DeckOpenRequest = {
  /** Talia do otwarcia; `null` = tylko pokaż zakładkę General. */
  deckId: string | null;
  tab?: PileTab;
  nonce: number;
};

type DeckSearchState = {
  request: DeckOpenRequest | null;
  open: (deckId: string | null, tab?: PileTab) => void;
};

export const useDeckSearchStore = create<DeckSearchState>((set, get) => ({
  request: null,
  open: (deckId, tab) =>
    set({ request: { deckId, tab, nonce: (get().request?.nonce ?? 0) + 1 } }),
}));

/** Identyfikatory talii, które da się otworzyć z wyszukiwarki. */
export type SearchDeckId =
  | "action"
  | "agenda"
  | "relic"
  | "secret"
  | "stage1"
  | "stage2"
  | "cultural"
  | "industrial"
  | "hazardous"
  | "frontier";
