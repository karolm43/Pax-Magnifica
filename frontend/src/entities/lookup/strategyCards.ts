import { strategyCards } from "@/entities/data/strategyCards";
import { indexBy } from "@/entities/lookup/indexBy";
import type { StrategyCardDefinition } from "@/entities/data/types";

const strategyCardsById = indexBy(strategyCards, (card) => card.id);

// WYBÓR WARIANTU karty strategii NALEŻY DO BACKENDU, nie do frontu. Przy wielu
// włączonych źródłach (np. Construction/Warfare z Thunder's Edge i PoK) kanoniczny
// wariant ustala rdzeń silnika (``core/registry.active_strategy_card_set_alias``,
// patrz docs/RULES.md 14) i zwraca go jako ``id`` w ``/strategy/cards``. Front NIE
// liczy już priorytetu źródeł — renderuje po ``id`` z backendu i robi WYŁĄCZNIE
// grafikę + czysty fallback OBRAZU (prezentacja).

/**
 * FALLBACK GRAFIKI (czysta prezentacja, bez rankingu źródeł): pierwszy niepusty
 * ``imageURL`` spośród wszystkich wariantów o danej initiative. Kanoniczny wariant
 * wybrany przez backend bywa bez grafiki w lokalnych danych (np. te4construction /
 * te6warfare mają ``imageURL: ""``), więc obraz bierzemy z DOWOLNEGO wariantu tej
 * samej initiative, który grafikę posiada (w praktyce pok*). Kolejność dowolna —
 * wystarczy jakikolwiek niepusty URL.
 */
function fallbackImageURL(initiative: number): string {
  for (const variant of strategyCards) {
    if (variant.initiative === initiative && variant.imageURL) {
      return variant.imageURL;
    }
  }
  return "";
}

/**
 * Zwraca kopię definicji z ``imageURL`` uzupełnionym (gdy pusty) grafiką dowolnego
 * wariantu o tej samej initiative. Treść i parametry (name, teksty, initiative,
 * kolor) pozostają z przekazanej definicji — zmieniamy tylko obraz (prezentacja).
 */
function withImageFallback(
  card: StrategyCardDefinition
): StrategyCardDefinition {
  if (card.imageURL) return card;
  const imageURL = fallbackImageURL(card.initiative);
  if (!imageURL) return card;
  return { ...card, imageURL };
}

/**
 * ŚCIEŻKA PREFEROWANA: lookup kanonicznego wariantu po ``id`` z backendu, z
 * fallbackiem GRAFIKI. To tędy komponent pobiera definicję karty.
 */
export function getStrategyCardById(
  id: string
): StrategyCardDefinition | undefined {
  const card = strategyCardsById.get(id);
  return card ? withImageFallback(card) : undefined;
}

/**
 * CIENKI FALLBACK dla zgodności: gdy ``id`` z backendu nie jest dostępne (albo nie
 * ma go w lokalnych danych), bierzemy DOWOLNY wariant o danej initiative + fallback
 * grafiki. BEZ rankingu źródeł — wybór wariantu to już rola backendu.
 */
export function getStrategyCardByInitiative(
  initiative: number
): StrategyCardDefinition | undefined {
  const card = strategyCards.find((c) => c.initiative === initiative);
  return card ? withImageFallback(card) : undefined;
}
