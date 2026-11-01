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
 * Lookup po INITIATIVE z użyciem mapy ``initiative → kanoniczny id`` z backendu
 * (``strategyCardIdMap``). To backend decyduje, KTÓRY wariant danej initiative jest
 * w grze (np. init 4/6 → Thunder's Edge, init 2 → Diplomacy z codexu), więc gdy
 * mapa podaje ``id`` — bierzemy dokładnie ten wariant przez ``getStrategyCardById``.
 *
 * DLACZEGO mapa jest KONIECZNA: wiele wariantów współdzieli tę samą initiative
 * (homebrew: anarchy, luminous, tispoon… część z PUSTYMI tekstami i inną nazwą,
 * np. init 2 ``anarchy2`` „Preparation"). Zwykłe ``find(initiative)`` łapało pierwszy
 * z tablicy — stąd błędna nazwa i puste „No primary/secondary ability". Mapa z
 * backendu wskazuje kanoniczny wariant jednoznacznie.
 *
 * FALLBACK (gdy brak mapy lub jej wpisu): preferuj wariant z aktywnych źródeł bazowych
 * (``base``/``pok``/``codex*``/``thunders_edge``) i z NIEPUSTĄ treścią — zamiast
 * pierwszego lepszego homebrew. Na końcu i tak uzupełniamy grafikę (``withImageFallback``).
 */
const CANONICAL_SOURCES = new Set([
  "base",
  "pok",
  "codex1",
  "codex2",
  "codex3",
  "codex4",
  "thunders_edge",
]);

export function getStrategyCardByInitiative(
  initiative: number,
  idMap?: Record<number, string>
): StrategyCardDefinition | undefined {
  // 1) Ścieżka preferowana: kanoniczny ``id`` z mapy backendu.
  const mappedId = idMap?.[initiative];
  if (mappedId) {
    const byId = getStrategyCardById(mappedId);
    if (byId) return byId;
  }

  // 2) Fallback bez mapy: wariant z aktywnego źródła bazowego i z treścią (nie
  //    pierwszy lepszy homebrew o tej initiative, który bywa pusty).
  const candidates = strategyCards.filter((c) => c.initiative === initiative);
  const canonical = candidates.find(
    (c) =>
      CANONICAL_SOURCES.has(c.source) &&
      (c.primaryTexts.length > 0 || c.secondaryTexts.length > 0)
  );
  const card =
    canonical ??
    candidates.find((c) => CANONICAL_SOURCES.has(c.source)) ??
    candidates[0];
  return card ? withImageFallback(card) : undefined;
}
