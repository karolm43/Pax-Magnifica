import type { OfferView } from "@/api/useOffers";

/**
 * Decyzje „wskaż okręt w tej bitwie" (np. ofiara Assault Cannon, naprawa Duranium Armor):
 * jedno wejście ``choice``, a każda opcja to jednostka (``meta.unit``) jednej ze stron walki.
 * Gracz klika okręt na polu bitwy — jak na planszy — zamiast szukać go w formularzu.
 * Obie strony mogą decydować NARAZ (np. obie mają Assault Cannon) — stąd mapa gracz → oferta
 * (pierwsza oferta danego gracza; następna pojawi się po rozstrzygnięciu).
 */
export function shipPickOffers(
  offers: OfferView[] | undefined,
  playerIds: string[],
): Map<string, OfferView> {
  const found = new Map<string, OfferView>();
  for (const offer of offers ?? []) {
    const [input, ...rest] = offer.inputs;
    if (!input || rest.length > 0 || input.kind !== "choice") continue;
    if (input.options.length === 0) continue;
    const owners = new Set(input.options.map((o) => o.meta?.player));
    const owner = [...owners][0];
    if (owners.size !== 1 || typeof owner !== "string") continue;
    if (!playerIds.includes(owner) || found.has(owner)) continue;
    if (!input.options.every((o) => typeof o.meta?.unit === "string")) continue;
    found.set(owner, offer);
  }
  return found;
}
