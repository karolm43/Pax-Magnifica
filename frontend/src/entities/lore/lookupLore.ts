import { getExploration } from "@/entities/lookup/explorations";
import { CARD_LORE, LORE_ALIASES, type LoreKind } from "./cardLore";
import { typeset } from "./typography";

/**
 * Tekst fabularny karty wpisany ręcznie w `cardLore.ts` (flavour). Zwraca `null`, gdy pole puste
 * albo karty brak — wtedy UI nic nie pokazuje. Karta z innej talii o tej samej nazwie (np. agendy
 * Absol: `absol_mutiny`) czyta lore karty oficjalnej przez `LORE_ALIASES`. Karta eksploracji typu
 * „Attach” z pustym polem czyta lore swojego attachmentu (to ta sama karta). Karty akcji, relikty,
 * eksploracja, systemy i planety mają tekst startowy skopiowany z assetów; czytają go przez
 * `lookupLoreOr` (poniżej), z fallbackiem do danych gry dla kart spoza `cardLore.ts`.
 */
export function lookupCardLore(kind: LoreKind, id: string | null | undefined): string | null {
  if (!id) return null;
  // Warianty „...stat” attachmentów (bonus do cech) czytają pole karty bazowej.
  const base = kind === "attachment" ? id.replace(/stat$/, "") : id;
  const key = LORE_ALIASES[kind]?.[base] ?? base;
  const text = CARD_LORE[kind][key];
  if (text && text.trim()) return typeset(text.trim());
  const attachmentId = kind === "exploration" ? getExploration(id)?.attachmentId : undefined;
  return attachmentId ? lookupCardLore("attachment", attachmentId) : null;
}

/**
 * Flavour karty, której tekst startowy pochodzi z danych gry (karty akcji, relikty, eksploracja,
 * systemy, planety): wpis w `cardLore.ts` wygrywa (pusty = świadomie brak lore); gdy karty tam
 * nie ma (np. fanowska), czytamy `fallback` z danych — bez kursywy `*...*`.
 */
export function lookupLoreOr(
  kind: LoreKind,
  id: string | null | undefined,
  fallback?: string | null,
): string | undefined {
  if (id && id in CARD_LORE[kind]) return lookupCardLore(kind, id) ?? undefined;
  const text = (fallback ?? "").replace(/^\*+|\*+$/g, "").trim();
  return text ? typeset(text) : undefined;
}
