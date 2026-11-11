import type {
  ProductionBody,
  ProductionPlanet,
  ProductionProducer,
  ProductionUnit,
} from "./useProduction";

/*
 * Rachunek okna produkcji (czyste funkcje; lustro reguł z core/production.py, RULES.md 33.3).
 * Silnik i tak waliduje - tu liczymy, żeby gracz widział limity ZANIM kliknie.
 */

export type CartLine = { baseType: string; zone: string; count: number };
export type Payment = { planets: string[]; tradeGoods: number };

export const SPACE = "space";

export const cartCount = (cart: CartLine[]): number =>
  cart.reduce((n, l) => n + l.count, 0);

export const countOf = (cart: CartLine[], baseType: string): number =>
  cart
    .filter((l) => l.baseType === baseType)
    .reduce((n, l) => n + l.count, 0);

/** Zmienia liczbę sztuk w linii (typ + strefa); linia o zerowej liczbie znika. */
export function bumpCart(
  cart: CartLine[],
  baseType: string,
  zone: string,
  delta: number,
): CartLine[] {
  const found = cart.find((l) => l.baseType === baseType && l.zone === zone);
  if (!found) {
    return delta > 0 ? [...cart, { baseType, zone, count: delta }] : cart;
  }
  return cart
    .map((l) => (l === found ? { ...l, count: l.count + delta } : l))
    .filter((l) => l.count > 0);
}

/** Koszt koszyka: sztuki tego samego typu łączą się w pary (fighter/infantry = 2 za koszt). */
export function cartCost(units: ProductionUnit[], cart: CartLine[]): number {
  let total = 0;
  for (const unit of units) {
    const n = countOf(cart, unit.baseType);
    if (n > 0) total += Math.ceil(n / unit.unitsPerCost) * unit.cost;
  }
  return total;
}

export const readyPlanets = (planets: ProductionPlanet[]) =>
  planets.filter((p) => !p.exhausted);

/** Wszystkie zasoby do wydania: gotowe planety + trade goods. */
export const fundsTotal = (view: ProductionBody): number =>
  readyPlanets(view.planets).reduce((n, p) => n + p.payValue, 0) +
  view.tradeGoods;

export const paymentTotal = (
  planets: ProductionPlanet[],
  payment: Payment,
): number =>
  planets
    .filter((p) => payment.planets.includes(p.planet))
    .reduce((n, p) => n + p.payValue, 0) + payment.tradeGoods;

/** Automatyczna płatność: najpierw planety (od największych), zbędne zdejmij, TG tylko na resztę. */
export function autoPay(
  planets: ProductionPlanet[],
  tradeGoods: number,
  cost: number,
): Payment {
  const need = Math.ceil(cost);
  if (need <= 0) return { planets: [], tradeGoods: 0 };
  const ranked = readyPlanets(planets)
    .filter((p) => p.payValue > 0)
    .sort((a, b) => b.payValue - a.payValue || a.planet.localeCompare(b.planet));
  const chosen: ProductionPlanet[] = [];
  let total = 0;
  for (const p of ranked) {
    if (total >= need) break;
    chosen.push(p);
    total += p.payValue;
  }
  for (const p of [...chosen].sort((a, b) => a.payValue - b.payValue)) {
    if (total - p.payValue >= need) {
      chosen.splice(chosen.indexOf(p), 1);
      total -= p.payValue;
    }
  }
  return {
    planets: chosen.map((p) => p.planet),
    tradeGoods: Math.min(tradeGoods, Math.max(0, need - total)),
  };
}

/**
 * Czy da się rozdzielić `counts` (typ → sztuki) między OSOBNE zdolności PRODUCTION (warunek Halla;
 * lustro `core/production.fits_producers`). Każda sztuka zajmuje 1 z wartości producenta, który
 * może ją wyprodukować (typ nie jest w jego `forbids`).
 */
export function fitsProducers(
  producers: ProductionProducer[],
  counts: Record<string, number>,
): boolean {
  const types = Object.keys(counts).filter((t) => counts[t] > 0);
  for (let mask = 1; mask < 1 << types.length; mask += 1) {
    const chosen = types.filter((_, i) => (mask >> i) & 1);
    const need = chosen.reduce((n, t) => n + counts[t], 0);
    const have = producers
      .filter((p) => chosen.some((t) => !p.forbids.includes(t)))
      .reduce((n, p) => n + p.value, 0);
    if (need > have) return false;
  }
  return true;
}

/** Już wyprodukowane w tej akcji + koszyk, wg typu. */
function demandWithCart(
  view: ProductionBody,
  cart: CartLine[],
): Record<string, number> {
  const total: Record<string, number> = { ...view.usedByType };
  for (const line of cart) {
    total[line.baseType] = (total[line.baseType] ?? 0) + line.count;
  }
  return total;
}

/** Powód, dla którego NIE wolno dodać kolejnej sztuki (null = wolno). */
export function whyNotAdd(
  view: ProductionBody,
  cart: CartLine[],
  unit: ProductionUnit,
  zone: string | null,
): string | null {
  const grant = view.grant;
  // Integrated Economy: brak limitu sztuk, liczy się tylko łączny koszt (poniżej).
  const costCapped = grant?.maxCost != null;
  if (!costCapped && view.remaining - cartCount(cart) <= 0) return "No production slots left";
  if (grant?.shipsOnly && unit.placement === "planet") return `${grant.source} produces ships only`;
  if (unit.placement === "space" && view.blockaded)
    return "Blockaded: enemy ships in the system";
  if (
    unit.reinforcements !== null &&
    countOf(cart, unit.baseType) >= unit.reinforcements
  )
    return "None left in reinforcements";
  if (unit.placement === "planet" && (!zone || !view.groundZones.includes(zone)))
    return "No place for ground forces (needs a dock on a planet)";
  const target = unit.placement === "space" ? SPACE : (zone ?? "");
  const next = bumpCart(cart, unit.baseType, target, 1);
  // Produkcja z karty nie korzysta z PRODUCTION jednostek, więc producentów nie sprawdzamy.
  if (!grant && !fitsProducers(view.producers, demandWithCart(view, next))) {
    return view.producers.some((p) => p.forbids.includes(unit.baseType))
      ? "The rest of your PRODUCTION can't make this unit"
      : "No production slots left";
  }
  const nextCost = cartCost(view.units, next);
  if (grant?.maxCost != null && nextCost > grant.maxCost)
    return `Over the planet's resource value (${grant.maxCost})`;
  if (nextCost > fundsTotal(view)) return "Not enough resources";
  return null;
}

/** Ile jeszcze sztuk tej jednostki można dodać (limit PRODUCTION, rezerwa, zasoby). */
export function maxMore(
  view: ProductionBody,
  cart: CartLine[],
  unit: ProductionUnit,
  zone: string | null,
): number {
  const target = unit.placement === "space" ? SPACE : (zone ?? "");
  let probe = cart;
  let n = 0;
  while (n < 99 && whyNotAdd(view, probe, unit, zone) === null) {
    probe = bumpCart(probe, unit.baseType, target, 1);
    n += 1;
  }
  return n;
}
