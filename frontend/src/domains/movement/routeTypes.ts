import { BASE_TYPE_BY_ASYNC } from "@/domains/map/components/UnitStack/cargo";

/**
 * Typy i czyste funkcje podglądu trasy ruchu (``GET /tactical/move-route``) oraz roboczego
 * wyboru jednostek (``moveDraft``). Bez UI i bez React — używają ich box, warstwa mapy i store.
 */

export type MoveRouteShip = {
  baseType: string;
  count: number;
  capacity: number;
  reachable: boolean;
  /** Dolatuje tylko z premią +1 do ruchu (Gravity Drive / Ionian Fuel Refinery): 1 sztuka. */
  boosted: boolean;
  reason: string;
};

export type MoveRouteCargo = {
  position: string;
  zone: string;
  baseType: string;
  count: number;
  capacityUsed: number;
};

export type MoveRouteData = {
  active: string | null;
  route: string[] | null;
  reason: string;
  alternatives: string[][];
  waypoints: string[];
  ships: MoveRouteShip[];
  cargo: MoveRouteCargo[];
};

/** Zaznaczona porcja: statek ze źródła albo ładunek z systemu na trasie. */
export type DraftPick = {
  kind: "ship" | "cargo";
  position: string;
  zone: string;
  baseType: string;
  count: number;
  max: number;
};

export type MoveDraft = {
  from: string;
  faction: string;
  /** Waypointy wybrane przez gracza (kolejność = kolejność przelotu). */
  via: string[];
  picks: Record<string, DraftPick>;
  route: MoveRouteData | null;
};

export type PickTarget = Pick<DraftPick, "kind" | "position" | "zone" | "baseType" | "max">;

export const pickKey = (t: Pick<DraftPick, "kind" | "position" | "zone" | "baseType">) =>
  `${t.kind}|${t.position}|${t.zone}|${t.baseType}`;

const ASYNC_BY_BASE_TYPE: Record<string, string> = Object.fromEntries(
  Object.entries(BASE_TYPE_BY_ASYNC).map(([asyncId, baseType]) => [baseType, asyncId]),
);

/** asyncId (klucz sprite'a) dla baseType z API. */
export function asyncOfBase(baseType: string): string {
  return ASYNC_BY_BASE_TYPE[baseType] ?? baseType;
}

/** Maksymalna liczba sztuk dla ładunku/statku wg aktualnej trasy (0 = brak na trasie). */
function maxFor(route: MoveRouteData, p: DraftPick): number {
  if (p.kind === "ship") {
    const ship = route.ships.find((s) => s.baseType === p.baseType);
    if (!ship || !ship.reachable) return 0;
    return ship.boosted ? 1 : ship.count;
  }
  const cargo = route.cargo.find(
    (c) => c.position === p.position && c.zone === p.zone && c.baseType === p.baseType,
  );
  return cargo?.count ?? 0;
}

/** Przycina zaznaczenie do tego, co nadal istnieje na (nowej) trasie. */
export function prunePicks(
  picks: Record<string, DraftPick>,
  route: MoveRouteData | null,
): Record<string, DraftPick> {
  if (!route?.route) return picks; // trasa chwilowo nielegalna: zachowaj wybór gracza
  const next: Record<string, DraftPick> = {};
  for (const [key, p] of Object.entries(picks)) {
    const max = maxFor(route, p);
    const count = Math.min(p.count, max);
    if (count > 0) next[key] = { ...p, count, max };
  }
  return next;
}

/** Pojemność zaznaczonej floty: suma capacity statków vs zajęcie przez ładunek. */
export function draftCapacity(draft: MoveDraft): { total: number; used: number } {
  let total = 0;
  let used = 0;
  for (const p of Object.values(draft.picks)) {
    if (p.kind === "ship") {
      const ship = draft.route?.ships.find((s) => s.baseType === p.baseType);
      total += (ship?.capacity ?? 0) * p.count;
    } else {
      const cargo = draft.route?.cargo.find(
        (c) => c.position === p.position && c.zone === p.zone && c.baseType === p.baseType,
      );
      used += (cargo?.capacityUsed ?? 1) * p.count;
    }
  }
  return { total, used };
}
