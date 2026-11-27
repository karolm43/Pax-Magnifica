import type {
  BattleAssignPlan,
  BattleSide,
  BattleUnit,
  HitTarget,
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
  /** Hit shield (Quantum Manipulator): it may only cancel a hit with Sustain Damage. */
  shield?: boolean;
  unit: BattleUnit;
};

export type Mark = "sustain" | "destroy" | "both";

/**
 * Ile trafień pokrywa znacznik egzemplarza. ``cancels`` = ile trafień anuluje jedno użycie
 * Sustain Damage (1; Non-Euclidean Shielding: 2 — wartość z backendu, ``sustainCancels``).
 */
export function markWeight(mark: Mark, cancels = 1): number {
  if (mark === "destroy") return 1;
  return mark === "sustain" ? cancels : cancels + 1;
}

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
        // Sustain nadany komponentem (Void Shielding) ma tylko ``sustainable`` egzemplarzy.
        canSustain:
          unit.sustain && !damaged && i - unit.damaged < unit.sustainable,
        shield: !!unit.shield,
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
  // A hit shield is not a ship: Sustain Damage or nothing (RULES.md 62.21).
  if (ship.shield) return current === undefined && ship.canSustain ? "sustain" : undefined;
  if (ship.canSustain) {
    if (current === undefined) return "sustain";
    if (current === "sustain") return "destroy";
    if (current === "destroy") return "both";
    return undefined;
  }
  return current === undefined ? "destroy" : undefined;
}

/** Suma pokrytych trafień. */
export function absorbed(marks: Record<string, Mark>, cancels = 1): number {
  return Object.values(marks).reduce(
    (sum, mark) => sum + markWeight(mark, cancels),
    0,
  );
}

/**
 * Czy znaczniki pokrywają DOKŁADNIE wymagane trafienia. Przy ``cancels > 1`` ostatnie użycie
 * Sustain może anulować mniej (zostało mniej trafień, F_letnev) — wtedy nadwyżka < ``cancels``
 * jest dozwolona, ale tylko gdy nic nie jest niszczone ponad potrzebę (same tarcze).
 */
export function isCovered(
  marks: Record<string, Mark>,
  required: number,
  cancels = 1,
): boolean {
  const total = absorbed(marks, cancels);
  if (total === required) return true;
  const values = Object.values(marks);
  return (
    cancels > 1 &&
    total > required &&
    total < required + cancels &&
    values.length > 0 &&
    values.every((mark) => mark === "sustain")
  );
}

/** Licznik „pokryto X / Y" (nadwyżka ostatniej tarczy przy ``cancels > 1`` nie wychodzi ponad Y). */
export function coveredCount(
  marks: Record<string, Mark>,
  required: number,
  cancels = 1,
): number {
  const total = absorbed(marks, cancels);
  return isCovered(marks, required, cancels) ? required : total;
}

/**
 * Klik egzemplarza: kolejny znacznik (``nextMark``), pomijając te, które pokryłyby więcej
 * trafień, niż trzeba — gdy żaden się nie mieści, znacznik znika.
 */
export function toggleMark(
  marks: Record<string, Mark>,
  ship: ShipEntity,
  required: number,
  cancels = 1,
): Record<string, Mark> {
  const rest = { ...marks };
  delete rest[ship.id];
  const fits = (mark: Mark) => {
    const next = { ...rest, [ship.id]: mark };
    return (
      absorbed(next, cancels) <= required || isCovered(next, required, cancels)
    );
  };
  let candidate = nextMark(ship, marks[ship.id]);
  while (candidate && !fits(candidate)) candidate = nextMark(ship, candidate);
  if (candidate) rest[ship.id] = candidate;
  return rest;
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
  cancels = 1,
): Record<string, Mark> {
  const marks: Record<string, Mark> = {};
  let left = required;
  // Hit shields cancel first: they are never lost to a hit (Quantum Manipulator).
  const shieldsFirst = [...ships].sort((a, b) => Number(!!b.shield) - Number(!!a.shield));
  for (const ship of shieldsFirst) {
    if (left <= 0) break;
    if (ship.canSustain) {
      marks[ship.id] = "sustain";
      left -= cancels;
    }
  }
  const weakestFirst = [...ships].filter((s) => !s.shield).sort(
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

/**
 * Egzemplarze, które wolno teraz oznaczyć. Gdy wymuszony cel obejmuje wszystkie trafienia
 * i jest na polu — tylko on (Devotion: wskazany statek, Impulse Core: nie-myśliwce „if able”).
 * Wskazany uszkodzony statek naprawiony w międzyczasie = ten sam typ, nieuszkodzony (jak silnik).
 */
export function assignableShips(
  ships: ShipEntity[],
  target: HitTarget | null | undefined,
  required: number,
): ShipEntity[] {
  if (!target || target.count < required) return ships;
  // A hit shield may cancel any of these hits, directed or not (F_nomad quantum-manipulator 1).
  const shields = ships.filter((s) => s.shield);
  const ofType = ships.filter((s) => target.types.includes(s.baseType));
  let damaged = target.damaged;
  if (damaged === true && !ofType.some((s) => s.damaged)) damaged = false;
  const hit =
    damaged === null ? ofType : ofType.filter((s) => s.damaged === damaged);
  if (hit.length === 0) return ships;
  // Wskazany jeden statek: wystarczy jeden egzemplarz (wszystkie tego stanu są równoważne).
  return [...(target.chooser && damaged !== null ? hit.slice(0, target.count) : hit), ...shields];
}

/**
 * "Sustain now" (C_action_cards/direct-hit/3): exactly one ship marked with a shield alone and
 * nothing else marked -> its base type, sent to ``POST /tactical/battle/sustain``; the other hits
 * wait until the opponent has used or declined Direct Hit. Hits directed at particular units
 * (``hitTarget``) are assigned in one go (RULES.md 53, user decision) -> ``null``.
 */
export function sustainNowType(
  ships: ShipEntity[],
  marks: Record<string, Mark>,
  hitTarget: HitTarget | undefined,
): string | null {
  if (hitTarget) return null;
  const marked = Object.entries(marks);
  if (marked.length !== 1 || marked[0][1] !== "sustain") return null;
  const ship = ships.find((s) => s.id === marked[0][0]);
  return ship && ship.canSustain ? ship.baseType : null;
}
