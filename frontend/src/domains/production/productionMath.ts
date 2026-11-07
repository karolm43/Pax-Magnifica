import type {
  ProductionBody,
  ProductionPlanet,
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
  readyPlanets(view.planets).reduce((n, p) => n + p.resources, 0) +
  view.tradeGoods;

export const paymentTotal = (
  planets: ProductionPlanet[],
  payment: Payment,
): number =>
  planets
    .filter((p) => payment.planets.includes(p.planet))
    .reduce((n, p) => n + p.resources, 0) + payment.tradeGoods;

/** Automatyczna płatność: najpierw planety (od największych), zbędne zdejmij, TG tylko na resztę. */
export function autoPay(
  planets: ProductionPlanet[],
  tradeGoods: number,
  cost: number,
): Payment {
  const need = Math.ceil(cost);
  if (need <= 0) return { planets: [], tradeGoods: 0 };
  const ranked = readyPlanets(planets)
    .filter((p) => p.resources > 0)
    .sort((a, b) => b.resources - a.resources || a.planet.localeCompare(b.planet));
  const chosen: ProductionPlanet[] = [];
  let total = 0;
  for (const p of ranked) {
    if (total >= need) break;
    chosen.push(p);
    total += p.resources;
  }
  for (const p of [...chosen].sort((a, b) => a.resources - b.resources)) {
    if (total - p.resources >= need) {
      chosen.splice(chosen.indexOf(p), 1);
      total -= p.resources;
    }
  }
  return {
    planets: chosen.map((p) => p.planet),
    tradeGoods: Math.min(tradeGoods, Math.max(0, need - total)),
  };
}

/** Powód, dla którego NIE wolno dodać kolejnej sztuki (null = wolno). */
export function whyNotAdd(
  view: ProductionBody,
  cart: CartLine[],
  unit: ProductionUnit,
  zone: string | null,
): string | null {
  if (view.remaining - cartCount(cart) <= 0) return "No production slots left";
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
  if (cartCost(view.units, next) > fundsTotal(view)) return "Not enough resources";
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
