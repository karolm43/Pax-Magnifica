import type { OfferView } from "@/api/useOffers";
import type { ShipEntity } from "./battleAssign";

type ChoiceInput = Extract<OfferView["inputs"][number], { kind: "choice" }>;
type ChoiceOption = ChoiceInput["options"][number];

/** Bieżący krok decyzji „wskaż okręt": które wejście oferty i czyje okręty są do kliknięcia. */
export type ShipPickStep = {
  offer: OfferView;
  input: ChoiceInput;
  /** Właściciel okrętów do kliknięcia (Devotion krok 2: przeciwnik decydującego). */
  owner: string;
  /** Wybory z wcześniejszych kroków tej oferty (klucz wejścia → id opcji). */
  chosen: Record<string, string>;
};

/** Jedyny właściciel opcji wejścia, gdy KAŻDA opcja to jednostka (``meta.unit``); inaczej ``null``. */
function unitOwner(input: OfferView["inputs"][number]): string | null {
  if (input.kind !== "choice" || input.options.length === 0) return null;
  if (!input.options.every((o) => typeof o.meta?.unit === "string")) return null;
  const owners = new Set(input.options.map((o) => o.meta?.player));
  const owner = [...owners][0];
  return owners.size === 1 && typeof owner === "string" ? owner : null;
}

/** Czy opcja opisuje ten egzemplarz: typ i — gdy silnik go podał — stan uszkodzenia. */
export function optionMatchesShip(option: ChoiceOption, ship: ShipEntity): boolean {
  if (String(option.meta?.unit) !== ship.baseType) return false;
  const damaged = option.meta?.damaged;
  return typeof damaged !== "boolean" || damaged === ship.damaged;
}

/**
 * Decyzje „wskaż okręt w tej bitwie" (ofiara Assault Cannon, naprawa Duranium Armor, Devotion):
 * KAŻDE wejście oferty to ``choice``, a jego opcje to jednostki (``meta.unit``) jednej ze stron
 * walki. Wejścia rozstrzygane po kolei — gracz klika okręt na polu bitwy zamiast szukać go
 * w formularzu (Devotion: najpierw własny krążownik/niszczyciel, potem okręt przeciwnika).
 * Obie strony mogą decydować NARAZ (np. obie mają Assault Cannon) — stąd mapa właściciel
 * okrętów → krok (pierwsza oferta; następna pojawi się po rozstrzygnięciu).
 */
export function shipPickSteps(
  offers: OfferView[] | undefined,
  playerIds: string[],
  chosen: Record<string, Record<string, string>> = {},
): Map<string, ShipPickStep> {
  const found = new Map<string, ShipPickStep>();
  const busy = new Set<string>();
  for (const offer of offers ?? []) {
    const owners = offer.inputs.map(unitOwner);
    if (owners.length === 0 || owners.some((o) => o === null || !playerIds.includes(o))) {
      continue;
    }
    // Jedna decyzja gracza naraz (kolejna oferta tego samego gracza czeka).
    if (busy.has(offer.player_id)) continue;
    const values = chosen[offer.id] ?? {};
    const index = offer.inputs.findIndex((input) => !(input.key in values));
    if (index < 0) continue;
    const owner = owners[index] as string;
    if (found.has(owner)) continue;
    busy.add(offer.player_id);
    found.set(owner, {
      offer,
      input: offer.inputs[index] as ChoiceInput,
      owner,
      chosen: values,
    });
  }
  return found;
}

/** Zgodność wstecz: mapa właściciel okrętów → oferta (tylko oferty w pierwszym kroku). */
export function shipPickOffers(
  offers: OfferView[] | undefined,
  playerIds: string[],
): Map<string, OfferView> {
  const steps = shipPickSteps(offers, playerIds);
  return new Map([...steps].map(([owner, step]) => [owner, step.offer]));
}
