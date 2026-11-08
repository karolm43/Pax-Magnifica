import { normalizeSearchText } from "./searchText";

/**
 * The kinds of thing board search can find. Each one renders somewhere on the
 * board or in a player area, tagged with a `data-search-key` built here.
 */
export type SearchKind =
  | "planet"
  | "system"
  | "faction"
  | "tech"
  | "relic"
  | "leader"
  | "promissory"
  | "secret"
  | "objective"
  | "law"
  | "strategy"
  /** Karta z talii (agenda, akcji, relikwia, eksploracja...) w oknie talii. */
  | "card";

export type SearchKey = `${SearchKind}:${string}`;

export function searchKey(kind: SearchKind, id: string): SearchKey {
  return `${kind}:${id}`;
}

/** Klucz karty w talii: talia + nazwa (identyczne kopie to jedna pozycja listy). */
export function cardSearchKey(deckId: string, name: string): SearchKey {
  return searchKey("card", `${deckId}:${normalizeSearchText(name)}`);
}

/**
 * Where a target is drawn. Map targets live inside the zoomed board, so their
 * highlight is scaled up to survive the zoom; a hex (a system, or a player's
 * stat area off the board's edge) highlights its own outline rather than its
 * rectangular box.
 */
export type SearchScope = "map" | "map-tile";

/** Attributes that make an element findable by board search. */
export function searchTarget(key: SearchKey, scope?: SearchScope) {
  return {
    "data-search-key": key,
    ...(scope ? { "data-search-scope": scope } : {}),
  };
}
