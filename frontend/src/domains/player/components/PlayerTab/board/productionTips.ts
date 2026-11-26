import type { BuildOption, EmpireStats } from "../empireStats";

/*
 * The production plate printed under a unit's silhouette on the faction sheet: how many the
 * player could build right now and what stops them building more. Everything comes from
 * `empireStats` (engine PRODUCTION per system, ready resources + trade goods, reinforcements,
 * fleet pool room) - no rule is recomputed here. The limit names WHERE the PRODUCTION comes from
 * (the system with the space dock), so a fighter box never reads as if the fighter produced.
 */

export type ProductionTip = {
  /** ok = can build now (the reason says what caps it), blocked = cannot build at all. */
  tone: "ok" | "blocked";
  /** Headline: "Can build 4", "Can't afford". */
  title: string;
  /** What limits it: "3 resources to spend", "fleet pool full (3/3)". */
  reason: string;
  /** Full explanation (hover). */
  detail: string;
};

/** "1 for 2" for units that come two for a cost (fighters, infantry). */
function costText(cost: number): string {
  return cost < 1 ? `${cost * 2} for 2` : String(cost);
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

/** Best system with PRODUCTION, e.g. "Jol / Nar produce 4". */
function bestDock(empire: EmpireStats): string {
  const best = empire.productionSystems[0];
  return best ? `${best.label} produce${best.label.includes("/") ? "" : "s"} ${best.value}` : "";
}

export function unitProductionTip(option: BuildOption, empire: EmpireStats): ProductionTip {
  const spend = `${empire.budget} to spend (ready resources + trade goods)`;
  const cost = `costs ${costText(option.cost)}`;
  if (empire.maxProduction === 0) {
    return {
      tone: "blocked",
      title: "Can't build",
      reason: "no space dock on the board",
      detail: `${option.name}: no unit of yours with PRODUCTION (a space dock) is on the board.`,
    };
  }
  if (option.max === 0) {
    switch (option.limitedBy) {
      case "reinforcements":
        return {
          tone: "blocked",
          title: "Can't build",
          reason: "all are on the board",
          detail: `${option.name}: none left in your reinforcements - destroyed units return there.`,
        };
      case "fleetPool":
        return {
          tone: "blocked",
          title: "Can't build",
          reason: `fleet pool full (${empire.largestFleet}/${empire.fleetPool})`,
          detail: `${option.name}: a new ship would exceed your fleet pool in every system with PRODUCTION. Add a token to the fleet pool or move ships out first.`,
        };
      default:
        return {
          tone: "blocked",
          title: "Can't afford",
          reason: `${cost} · you have ${empire.budget}`,
          detail: `${option.name}: ${cost}, you have ${spend}.`,
        };
    }
  }
  const reason: Record<BuildOption["limitedBy"], string> = {
    resources: `${empire.budget} resources to spend`,
    production: bestDock(empire),
    reinforcements: `${option.reinforcements ?? option.max} left in reinforcements`,
    fleetPool: `room for ${empire.fleetRoom ?? option.max} in the fleet pool`,
  };
  return {
    tone: "ok",
    title: `Can build ${option.max}`,
    reason: reason[option.limitedBy],
    detail:
      `${option.name}: ${cost}. Right now you could build up to ${option.max}, limited by ` +
      `${reason[option.limitedBy]}. You have ${spend}; best PRODUCTION: ${bestDock(empire)}.`,
  };
}

/** Space dock plate: where the player can produce and how much. */
export function dockProductionTip(empire: EmpireStats): ProductionTip {
  const systems = empire.productionSystems;
  if (systems.length === 0) {
    return {
      tone: "blocked",
      title: "Not producing",
      reason: "no space dock on the board",
      detail: "No unit with PRODUCTION on the board - you cannot produce until you place a space dock.",
    };
  }
  const best = systems[0];
  const list = systems.map((s) => `${s.label} ${s.value}`).join(", ");
  return {
    tone: "ok",
    title: `Produces up to ${best.value}`,
    reason: `in ${best.label}${systems.length > 1 ? ` · +${plural(systems.length - 1, "system")}` : ""}`,
    detail: `PRODUCTION per system: ${list}. You have ${empire.budget} to spend (ready resources + trade goods).`,
  };
}
