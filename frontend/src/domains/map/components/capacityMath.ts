import type { CapacityView } from "@/api/useBoardEditor";

/**
 * Rachunek limitu pojemności po stronie UI (RULES.md 39.6) — ta sama formuła co
 * ``core/capacity.py`` (``CapacityReport.excess_for``), żeby modal na bieżąco pokazywał,
 * czy wybór usuwa dokładnie tyle, ile trzeba. Rozstrzyga i tak backend (422 z powodem).
 */

type Pick = Record<string, number>;

/** Ładunek, który ZOSTANIE w przestrzeni po usunięciu ``remove``. */
export function remainingCargo(view: CapacityView, remove: Pick): Pick {
  const out: Pick = {};
  for (const c of view.cargo) {
    out[c.baseType] = Math.max(0, c.count - (remove[c.baseType] ?? 0));
  }
  return out;
}

/** Nadwyżka (w jednostkach pojemności) dla podanego ładunku. Myśliwce najpierw na dok. */
export function excessFor(view: CapacityView, cargo: Pick): number {
  const cost = (bt: string) =>
    view.cargo.find((c) => c.baseType === bt)?.cost ?? 1;
  const fighters = cost("fighter") * (cargo.fighter ?? 0);
  const total = Object.entries(cargo).reduce(
    (sum, [bt, n]) => sum + cost(bt) * n,
    0,
  );
  const need = total - Math.min(fighters, view.fighterOnly);
  return Math.max(0, need - view.general);
}

/** Czy usunięcie jest poprawne: brak nadwyżki i żadna usunięta sztuka nie była zbędna. */
export function removalStatus(
  view: CapacityView,
  remove: Pick,
): "over" | "exact" | "tooMany" {
  const left = remainingCargo(view, remove);
  if (excessFor(view, left) > 0) return "over";
  for (const [bt, n] of Object.entries(remove)) {
    if (n <= 0) continue;
    if (excessFor(view, { ...left, [bt]: (left[bt] ?? 0) + 1 }) === 0)
      return "tooMany";
  }
  return "exact";
}
