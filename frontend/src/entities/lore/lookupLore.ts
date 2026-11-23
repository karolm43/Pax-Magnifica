import { CARD_LORE, type LoreKind } from "./cardLore";

/**
 * Tekst fabularny karty wpisany ręcznie w `cardLore.ts` (flavour). Zwraca `null`, gdy pole puste
 * albo karty brak — wtedy UI nic nie pokazuje. Flavour z assetów AsyncTI4 (akcje, relikty,
 * eksploracja) czytają ich własne komponenty z pola `flavorText`.
 */
export function lookupCardLore(kind: LoreKind, id: string | null | undefined): string | null {
  if (!id) return null;
  const text = CARD_LORE[kind][id];
  return text && text.trim() ? text.trim() : null;
}
