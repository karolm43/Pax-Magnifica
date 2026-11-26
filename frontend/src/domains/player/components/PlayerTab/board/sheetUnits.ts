import { getUnitData } from "@/entities/lookup/units";
import { getTechData } from "@/entities/lookup/tech";
import type { Unit } from "@/entities/data/types";

/*
 * What a unit box of the faction sheet prints, derived from unit data only: the stat bar,
 * the keyword line and the UPGRADE strip. No numbers of its own.
 */

export type StatBox = {
  label: "Cost" | "Combat" | "Move" | "Capacity";
  value: string;
  /** Combat dice, or how many units the cost buys (fighters, infantry). */
  times?: number;
};

type Modifiers = {
  bonusCombatDice?: number;
  combatValueModifier?: number;
  costModifier?: number;
};

/** Only the boxes the printed sheet shows for this kind of unit; "–" for an empty printed box. */
export function statBoxes(unit: Unit, modifiers: Modifiers = {}): StatBox[] {
  const { bonusCombatDice = 0, combatValueModifier = 0, costModifier = 0 } = modifiers;
  const boxes: StatBox[] = [];
  if (unit.cost != null) {
    const cost = unit.cost + costModifier;
    boxes.push(
      cost < 1
        ? { label: "Cost", value: "1", times: Math.round(1 / cost) }
        : { label: "Cost", value: String(cost) },
    );
  }
  if (unit.combatHitsOn != null) {
    const dice = (unit.combatDieCount ?? 1) + bonusCombatDice;
    boxes.push({
      label: "Combat",
      value: String(unit.combatHitsOn + combatValueModifier),
      ...(dice > 1 ? { times: dice } : {}),
    });
  }
  const moves = Boolean(unit.isShip) || unit.moveValue != null;
  if (moves) boxes.push({ label: "Move", value: String(unit.moveValue ?? "–") });
  // Printed: ships have a capacity box (destroyers and fighters don't); structures only if they move.
  const hasCapacityBox = unit.isShip
    ? unit.capacityValue != null || !["destroyer", "fighter"].includes(unit.baseType)
    : unit.moveValue != null && unit.capacityValue != null;
  if (hasCapacityBox) boxes.push({ label: "Capacity", value: String(unit.capacityValue ?? "–") });
  return boxes;
}

function dice(label: string, hitsOn?: number, count?: number): string[] {
  if (!hitsOn) return [];
  return [`${label} ${hitsOn}${(count ?? 1) > 1 ? ` (x${count})` : ""}`];
}

export function unitKeywords(unit: Unit): string[] {
  const production = unit.productionValue;
  return [
    ...(unit.sustainDamage ? ["Sustain Damage"] : []),
    ...dice("Bombardment", unit.bombardHitsOn, unit.bombardDieCount),
    ...dice("Anti-Fighter Barrage", unit.afbHitsOn, unit.afbDieCount),
    ...(unit.planetaryShield ? ["Planetary Shield"] : []),
    ...dice("Space Cannon", unit.spaceCannonHitsOn, unit.spaceCannonDieCount),
    // "+2" style values depend on the planet: the sheet prints "Production X".
    ...(production
      ? [`Production ${String(production).startsWith("+") ? "X" : production}`]
      : []),
  ];
}

export type UpgradeStrip = {
  /** Prerequisite letters of the upgrade technology (B, G, R, Y). */
  requirements: string;
  researched: boolean;
  techName: string;
};

export function upgradeStrip(unit: Unit): UpgradeStrip | null {
  const upgraded = unit.upgradesFromUnitId ? unit : undefined;
  const target =
    upgraded ?? (unit.upgradesToUnitId ? getUnitData(unit.upgradesToUnitId) : undefined);
  if (!target?.requiredTechId) return null;
  const tech = getTechData(target.requiredTechId);
  if (!tech) return null;
  return {
    requirements: tech.requirements ?? "",
    researched: upgraded !== undefined,
    techName: tech.name,
  };
}

const COLOR_NAME: Record<string, string> = { B: "blue", G: "green", R: "red", Y: "yellow" };

/** "BBY" -> "2 blue, 1 yellow" (spoken form of the prerequisite icons). */
export function prerequisiteText(requirements: string): string {
  const counts = new Map<string, number>();
  for (const letter of requirements) {
    const color = COLOR_NAME[letter];
    if (color) counts.set(color, (counts.get(color) ?? 0) + 1);
  }
  if (counts.size === 0) return "no prerequisites";
  return [...counts].map(([color, n]) => `${n} ${color}`).join(", ");
}
