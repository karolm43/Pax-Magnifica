import { strategyCards } from "@/entities/data/strategyCards";
import { indexBy } from "@/entities/lookup/indexBy";
import type { StrategyCardDefinition } from "@/entities/data/types";

const strategyCardsById = indexBy(strategyCards, (card) => card.id);

// Priorytet źródeł (od NAJWYŻSZEGO do najniższego). Decyzja projektowa: wszystkie
// dodatki włączone, Thunder's Edge najwyżej. Gdy wiele włączonych źródeł dostarcza
// wariant tej samej karty strategii (np. Construction/Warfare), obowiązuje wariant
// z najwyższego źródła. Patrz docs/RULES.md 14.
const SOURCE_PRIORITY = [
  "thunders_edge",
  "pok",
  "codex4",
  "codex3",
  "codex2",
  "codex1",
  "base",
];

/**
 * Pozycja źródła w rankingu priorytetu (im MNIEJ, tym WYŻSZY priorytet). Źródła
 * spoza listy (homebrew: anarchy, luminous, salliance, twilights_fall, miltymod,
 * monuments, project_pi, ignis_aurora, riftset, voices_of_the_council, asteroid,
 * other, ...) dostają najniższy priorytet.
 */
function sourceRank(source: string): number {
  const rank = SOURCE_PRIORITY.indexOf(source);
  return rank === -1 ? SOURCE_PRIORITY.length : rank;
}

/** Warianty tej samej initiative, posortowane rosnąco wg priorytetu źródła. */
function variantsByPriority(initiative: number): StrategyCardDefinition[] {
  return strategyCards
    .filter((card) => card.initiative === initiative)
    .sort((a, b) => sourceRank(a.source) - sourceRank(b.source));
}

/**
 * Pierwszy niepusty `imageURL` spośród wariantów danej initiative (wg priorytetu
 * źródła). Pozwala na FALLBACK GRAFIKI: wariant najwyższego źródła daje treść, ale
 * jego grafika bywa pusta (np. te4construction/te6warfare), więc obraz bierzemy
 * z wariantu niższego źródła (np. pok4construction / pok6warfare).
 */
function fallbackImageURL(initiative: number): string {
  for (const variant of variantsByPriority(initiative)) {
    if (variant.imageURL) return variant.imageURL;
  }
  return "";
}

/**
 * Zwraca kopię definicji z `imageURL` uzupełnionym (gdy pusty) grafiką wariantu
 * o tej samej initiative z najwyższego źródła, które taką grafikę posiada. Treść
 * i parametry (name, teksty, initiative, kolor) pozostają z przekazanej definicji.
 */
function withImageFallback(
  card: StrategyCardDefinition
): StrategyCardDefinition {
  if (card.imageURL) return card;
  const imageURL = fallbackImageURL(card.initiative);
  if (!imageURL) return card;
  return { ...card, imageURL };
}

export function getStrategyCardById(
  id: string
): StrategyCardDefinition | undefined {
  return strategyCardsById.get(id);
}

export function getStrategyCardByInitiative(
  initiative: number,
  strategyCardIdMap?: Record<number, string>
): StrategyCardDefinition | undefined {
  // Jawnie zmapowane id (np. z web-data) jest nadrzędnym wyborem wariantu, ale i tak
  // stosujemy fallback grafiki z wariantów tej samej initiative.
  const mappedCardId = strategyCardIdMap?.[initiative];
  if (mappedCardId) {
    const mapped = getStrategyCardById(mappedCardId);
    if (mapped) return withImageFallback(mapped);
  }

  // Brak mapy: wybór kanoniczny = wariant o najwyższym priorytecie źródła.
  const [canonical] = variantsByPriority(initiative);
  return canonical ? withImageFallback(canonical) : undefined;
}
