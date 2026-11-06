import type {
  BattleAssignPlan,
  BattleSide,
  BattleUnit,
} from "@/api/useBoardEditor";

/**
 * Logika przypisania strat w oknie pola bitwy (RULES.md 39 W7/W8) — czysta, bez UI.
 *
 * Statki strony rozwijamy w POJEDYNCZE egzemplarze (``ShipEntity``), żeby gracz klikał
 * konkretny okręt na polu bitwy. Każdy egzemplarz dostaje „znacznik": Sustain Damage,
 * zniszczenie albo oba (nieuszkodzony z Sustain może przyjąć dwa trafienia). Plan wysyłany
 * do silnika to sumy per typ — silnik i tak waliduje (422 z powodem).
 */

export type ShipEntity = {
  /** Stabilny identyfikator egzemplarza: ``<baseType>-<indeks>``. */
  id: string;
  baseType: string;
  asyncId: string;
  name: string;
  damaged: boolean;
  /** Może jeszcze użyć Sustain Damage (ma zdolność i nie jest uszkodzony). */
  canSustain: boolean;
  unit: BattleUnit;
};

export type Mark = "sustain" | "destroy" | "both";

/** Ile trafień pokrywa znacznik egzemplarza. */
export const MARK_WEIGHT: Record<Mark, number> = {
  sustain: 1,
  destroy: 1,
  both: 2,
};

/** Rozwija jednostki strony w egzemplarze; pierwsze ``damaged`` sztuk danego typu są uszkodzone. */
export function expandShips(side: BattleSide | null): ShipEntity[] {
  if (!side) return [];
  const ships: ShipEntity[] = [];
  for (const unit of side.units) {
    for (let i = 0; i < unit.count; i += 1) {
      const damaged = i < unit.damaged;
      ships.push({
        id: `${unit.baseType}-${i}`,
        baseType: unit.baseType,
        asyncId: unit.asyncId,
        name: unit.name,
        damaged,
        canSustain: unit.sustain && !damaged,
        unit,
      });
    }
  }
  return ships;
}

/** Kolejny znacznik po kliknięciu: z Sustain → sustain → destroy → oba → brak. */
export function nextMark(
  ship: ShipEntity,
  current: Mark | undefined,
): Mark | undefined {
  if (ship.canSustain) {
    if (current === undefined) return "sustain";
    if (current === "sustain") return "destroy";
    if (current === "destroy") return "both";
    return undefined;
  }
  return current === undefined ? "destroy" : undefined;
}

/** Suma pokrytych trafień. */
export function absorbed(marks: Record<string, Mark>): number {
  return Object.values(marks).reduce((sum, mark) => sum + MARK_WEIGHT[mark], 0);
}

/**
 * Plan dla silnika: sustain (egzemplarz staje się uszkodzony), destroy (nieuszkodzony
 * niszczony) i destroyDamaged (uszkodzony niszczony — także ten właśnie uszkodzony).
 */
export function planFromMarks(
  ships: ShipEntity[],
  marks: Record<string, Mark>,
): BattleAssignPlan {
  const plan: BattleAssignPlan = {
    sustain: {},
    destroy: {},
    destroyDamaged: {},
  };
  const add = (bucket: Record<string, number>, baseType: string) => {
    bucket[baseType] = (bucket[baseType] ?? 0) + 1;
  };
  for (const ship of ships) {
    const mark = marks[ship.id];
    if (!mark) continue;
    if (mark === "sustain" || mark === "both") add(plan.sustain, ship.baseType);
    if (mark === "both" || (mark === "destroy" && ship.damaged)) {
      add(plan.destroyDamaged, ship.baseType);
    } else if (mark === "destroy") {
      add(plan.destroy, ship.baseType);
    }
  }
  return plan;
}

/**
 * Podpowiedź „Auto": najpierw Sustain Damage, potem niszczymy najsłabsze jednostki
 * (najwyższy próg trafienia = najsłabsza walka; uszkodzone przed nieuszkodzonymi),
 * a gdy trafień wciąż zostaje — dobijamy egzemplarze, które użyły Sustain.
 */
export function autoMarks(
  ships: ShipEntity[],
  required: number,
): Record<string, Mark> {
  const marks: Record<string, Mark> = {};
  let left = required;
  for (const ship of ships) {
    if (left <= 0) break;
    if (ship.canSustain) {
      marks[ship.id] = "sustain";
      left -= 1;
    }
  }
  const weakestFirst = [...ships].sort(
    (a, b) =>
      b.unit.baseHitsOn - a.unit.baseHitsOn ||
      Number(b.damaged) - Number(a.damaged),
  );
  for (const ship of weakestFirst) {
    if (left <= 0) break;
    if (marks[ship.id]) continue;
    marks[ship.id] = "destroy";
    left -= 1;
  }
  for (const ship of weakestFirst) {
    if (left <= 0) break;
    if (marks[ship.id] === "sustain") {
      marks[ship.id] = "both";
      left -= 1;
    }
  }
  return marks;
}
