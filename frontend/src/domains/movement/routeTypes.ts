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
  /** Dolatuje sam, bez premii i bez towarzyszy. */
  alone: boolean;
  /** Typy statków, z którymi dolatuje bez premii, gdy lecą razem (Gravleash Maneuvers). */
  withShips: string[];
  /** Zestawy premii (``gravity_drive`` / ``tempesta``), z którymi dolatuje. */
  bonusOptions: string[][];
  /** Ile sztuk wolno ruszyć z premią (1; z Gravleash cała grupa). */
  bonusMax: number;
  reason: string;
};

/** Ile sztuk statku wolno zaznaczyć: bez premii wszystkie, tylko z premią - ``bonusMax``. */
export function shipMax(ship: MoveRouteShip): number {
  if (!ship.reachable) return 0;
  return ship.alone || ship.withShips.length > 0 ? ship.count : ship.bonusMax;
}

/**
 * Problemy zaznaczenia, których backend i tak nie przepuści - pokazujemy je od razu:
 * statek dolatujący tylko razem z innym typem (Gravleash) bez tego towarzysza i bez premii.
 */
export function draftProblems(
  draft: MoveDraft,
  nameOf: (baseType: string) => string,
  bonusesOn: boolean,
): string[] {
  const route = draft.route;
  if (!route) return [];
  const picked = new Set(
    Object.values(draft.picks)
      .filter((p) => p.kind === "ship" && p.count > 0)
      .map((p) => p.baseType),
  );
  const problems: string[] = [];
  for (const ship of route.ships) {
    if (!picked.has(ship.baseType) || ship.alone || ship.withShips.length === 0) continue;
    if (ship.withShips.some((bt) => picked.has(bt))) continue;
    if (bonusesOn && ship.bonusOptions.length > 0) continue;
    problems.push(
      `${nameOf(ship.baseType)} reaches only together with ${ship.withShips.map(nameOf).join(" or ")}.`,
    );
  }
  return problems;
}

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
  /** Systemy trasy będące gravity rift (+1 do ruchu, d10: 1–3 usuwa statek). */
  riftNodes: string[];
  /** Czy statki rzucają za szczeliny (Circlet of the Void: +1 bez rzutu). */
  riftRolls: boolean;
  /** Premie +1 do ruchu, które gracz może teraz włączyć. */
  bonuses: string[];
  /** Ion Storm w systemie z własnym wormholem tego typu: gracz wybiera wormhole (pozycja). */
  ionStormChoice?: string | null;
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
    return ship ? shipMax(ship) : 0;
  }
  const cargo = route.cargo.find(
    (c) => c.position === p.position && c.zone === p.zone && c.baseType === p.baseType,
  );
  return cargo?.count ?? 0;
}

function asCargoIfNeeded(route: MoveRouteData, p: DraftPick): DraftPick {
  if (p.kind !== "ship" || route.ships.some((s) => s.baseType === p.baseType)) return p;
  const cargo = route.cargo.find(
    (c) => c.position === p.position && c.zone === "space" && c.baseType === p.baseType,
  );
  return cargo ? { ...p, kind: "cargo", zone: "space" } : p;
}

/**
 * Ile sztuk tego typu ze startu zajmuje DRUGA rola. Fighter II ze startu bywa jednocześnie na
 * liście statków (leci sam - liczy się do fleet pool w celu) i ładunku (jedzie na nosicielu);
 * te same sztuki nie mogą być w obu miejscach naraz (backend: ``move_fleet``).
 */
export function otherRoleCount(
  picks: Record<string, DraftPick>,
  from: string,
  target: Pick<DraftPick, "kind" | "position" | "zone" | "baseType">,
): number {
  if (target.position !== from || target.zone !== "space") return 0;
  const other = target.kind === "ship" ? "cargo" : "ship";
  return (
    picks[pickKey({ kind: other, position: from, zone: "space", baseType: target.baseType })]
      ?.count ?? 0
  );
}

/** Przycina zaznaczenie do tego, co nadal istnieje na (nowej) trasie. */
export function prunePicks(
  picks: Record<string, DraftPick>,
  route: MoveRouteData | null,
): Record<string, DraftPick> {
  if (!route?.route) return picks; // trasa chwilowo nielegalna: zachowaj wybór gracza
  const next: Record<string, DraftPick> = {};
  // Najpierw statki: ładunek ze startu dostaje to, co zostało po lecących samych.
  const ordered = Object.values(picks).sort(
    (a, b) => Number(a.kind === "cargo") - Number(b.kind === "cargo"),
  );
  for (const p of ordered) {
    // Myśliwiec/piechota wybrane jako „statek”, który sam nie doleci (np. Fighter II poza
    // zasięgiem) - jedzie jako ładunek ze startu, zamiast znikać z wyboru.
    const pick = asCargoIfNeeded(route, p);
    const key = pickKey(pick);
    const have = next[key]?.count ?? 0;
    const start = route.route[0];
    const max = maxFor(route, pick);
    const room = max - (pick.kind === "cargo" ? otherRoleCount(next, start, pick) : 0);
    const count = Math.min(have + pick.count, Math.max(room, 0));
    if (count > 0) next[key] = { ...pick, count, max };
    else delete next[key];
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
