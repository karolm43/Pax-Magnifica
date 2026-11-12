import { findSearchHits, jumpToSearchHit } from "./searchHits";
import { searchKey, type SearchKey } from "./searchKeys";

/*
 * „Gdzie to jest?” dla okien decyzji: opcja wskazująca planetę albo system podświetla go na
 * mapie tymi samymi znacznikami co wyszukiwarka (`data-search-match/current`). Podgląd
 * (`body[data-map-peek]`) robi okna prawie przezroczystymi, żeby cel było widać spod nich.
 */

const MATCH_ATTR = "data-search-match";
const CURRENT_ATTR = "data-search-current";
const PEEK_ATTR = "data-map-peek";

/** Elementy oznaczone przez podgląd - zdejmujemy tylko własne znaczniki, nie wyszukiwarki. */
let marked: HTMLElement[] = [];

/** Klucze mapy, które może oznaczać opcja: id planety albo pozycja systemu. */
export function mapRefKeys(value: unknown, meta?: Record<string, unknown>): SearchKey[] {
  const keys: SearchKey[] = [];
  const add = (kind: "planet" | "system", id: unknown) => {
    if (typeof id === "string" && id) keys.push(searchKey(kind, id));
  };
  add("planet", meta?.planet);
  add("system", meta?.system);
  add("system", meta?.position);
  if (typeof value === "string") {
    add("planet", value);
    add("system", value);
  }
  return keys;
}

/** Cele na planszy (tylko mapa, nie karty w obszarach graczy). */
export function mapHits(keys: SearchKey[]): HTMLElement[] {
  return keys.length > 0 ? findSearchHits(keys, true) : [];
}

/** Podświetla cele; ``peek`` dodatkowo prześwietla okna, ``jump`` przewija mapę do celu. */
export function showOnMap(
  keys: SearchKey[],
  { peek = false, jump = false }: { peek?: boolean; jump?: boolean } = {},
): boolean {
  clearMapMarks();
  const hits = mapHits(keys);
  if (hits.length === 0) return false;
  hits.forEach((hit) => hit.setAttribute(MATCH_ATTR, ""));
  if (jump) jumpToSearchHit(hits[0]);
  else hits[0].setAttribute(CURRENT_ATTR, "");
  marked = hits;
  if (peek) document.body.setAttribute(PEEK_ATTR, "");
  return true;
}

/** Zdejmuje podświetlenie i podgląd. */
export function clearMapMarks(): void {
  marked.forEach((hit) => {
    hit.removeAttribute(MATCH_ATTR);
    hit.removeAttribute(CURRENT_ATTR);
  });
  marked = [];
  document.body.removeAttribute(PEEK_ATTR);
}
