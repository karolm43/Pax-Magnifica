import { describe, expect, it } from "vitest";
import type { PlayerData } from "@/entities/data/types";
import type { Tile } from "@/entities/game/types";
import { getUnitData, lookupUnit } from "@/entities/lookup/units";
import { empireStats } from "./empireStats";
import { commanderTips } from "./commanderTips";

function player(over: Partial<PlayerData> = {}): PlayerData {
  return {
    discordId: "p1",
    faction: "hacan",
    color: "yellow",
    flexibleDisplayName: "Hacan",
    totalVps: 0,
    scs: [],
    exhaustedSCs: [],
    planets: ["wellon", "meer", "lodor", "arnor"],
    exhaustedPlanets: ["meer"],
    resources: 3,
    tg: 2,
    fleetCC: 3,
    leaders: [],
    unitsOwned: ["carrier", "cruiser", "destroyer", "dreadnought", "fighter", "infantry", "spacedock", "pds", "hacan_flagship", "hacan_mech"],
    unitCounts: {
      dd: { unitCap: 8, deployedCount: 2 },
      ca: { unitCap: 8, deployedCount: 1 },
      dn: { unitCap: 5, deployedCount: 5 },
      ff: { unitCap: 10, deployedCount: 4 },
      gf: { unitCap: 12, deployedCount: 3 },
      sd: { unitCap: 3, deployedCount: 1 },
    },
    ...over,
  } as unknown as PlayerData;
}

function tile(over: Partial<Tile>): Tile {
  return { unitsByFaction: {}, planets: {}, ...over } as unknown as Tile;
}

const unit = (entityId: string, count: number) => ({ entityId, entityType: "unit" as const, count });

const TILES: Record<string, Tile> = {
  // Dom: same moje jednostki, PRODUCTION 4.
  "101": tile({
    unitsByFaction: { hacan: [unit("dd", 2), unit("ca", 1), unit("ff", 4)] },
    planets: { arnor: { controlledBy: "hacan", unitsByFaction: {} } } as unknown as Tile["planets"],
    productionByColor: { yellow: 4 },
  }),
  // Wspólny system z innym graczem.
  "202": tile({
    unitsByFaction: { hacan: [unit("dn", 3)], sol: [unit("dd", 1)] },
    productionByColor: { yellow: 0, blue: 2 },
  }),
  // Cudzy system.
  "303": tile({ unitsByFaction: { sol: [unit("ca", 1)] } }),
};

describe("empireStats", () => {
  it("liczy planety wg cech i specjalizacje tylko na gotowych planetach", () => {
    const s = empireStats(player(), TILES);
    expect(s.planets).toEqual({ total: 4, ready: 3, legendary: 0 });
    expect(s.traits).toEqual({ cultural: 1, hazardous: 1, industrial: 2 });
    // meer (WARFARE) jest wyczerpana - nie liczy się.
    expect(s.skips).toEqual({ biotic: 0, propulsion: 0, cybernetic: 1, warfare: 0 });
  });

  it("liczy systemy, największą flotę bez myśliwców i najwyższe PRODUCTION gracza", () => {
    const s = empireStats(player(), TILES);
    expect(s.systems).toEqual({ present: 2, controlled: 1 });
    expect(s.largestFleet).toBe(3);
    expect(s.fleetPool).toBe(3);
    expect(s.maxProduction).toBe(4);
    expect(s.forces).toEqual({ ships: 8, fighters: 4, ground: 3, docks: 1, pds: 0 });
  });

  it("kalkulator budowy: koszt z danych, limit zasobów/PRODUCTION/posiłków", () => {
    // Pula floty 8: przy doku stoją 3 statki, więc miejsca (5) wystarcza - nie ogranicza.
    const s = empireStats(player({ fleetCC: 8 }), TILES);
    expect(s.budget).toBe(5); // 3 gotowe zasoby + 2 TG
    const byId = Object.fromEntries(s.build.map((b) => [b.asyncId, b]));
    const p = player();
    const cost = (id: string) => getUnitData(lookupUnit(id, "hacan", p)!.id)!.cost!;
    // Niszczyciele: tanie, więc ogranicza PRODUCTION 4.
    expect(byId.dd.max).toBe(Math.min(Math.floor(5 / cost("dd")), 4, 6));
    // Pancerniki: wszystkie na planszy - brak posiłków.
    expect(byId.dn.max).toBe(0);
    expect(byId.dn.limitedBy).toBe("reinforcements");
    expect(s.depleted).toContain(lookupUnit("dn", "hacan", p)!.name);
    // Myśliwce: dwa za koszt, żetony bez limitu posiłków, każdy liczy się do PRODUCTION.
    expect(byId.ff.reinforcements).toBeNull();
    expect(byId.ff.max).toBe(4);
    expect(byId.ff.limitedBy).toBe("production");
  });

  it("Shipyard: pełna pula floty w systemie z PRODUCTION blokuje statki, nie myśliwce", () => {
    // Dom (PRODUCTION 4) ma 3 nie-myśliwce przy puli 3 - nowy okręt i tak trzeba by usunąć.
    const s = empireStats(player({ influence: 4.5 } as Partial<PlayerData>), TILES);
    expect(s.fleetRoom).toBe(0);
    const byId = Object.fromEntries(s.build.map((b) => [b.asyncId, b]));
    expect(byId.dd).toMatchObject({ max: 0, limitedBy: "fleetPool" });
    expect(byId.ff.limitedBy).not.toBe("fleetPool");
    expect(byId.gf.limitedBy).not.toBe("fleetPool");
    expect(s.readyInfluence).toBe(4);
  });

  it("Shipyard: bez systemu z PRODUCTION pula floty nie jest liczona", () => {
    const s = empireStats(player(), { "202": TILES["202"] });
    expect(s.fleetRoom).toBeNull();
    expect(s.build.some((b) => b.limitedBy === "fleetPool")).toBe(false);
  });

  it("porady: pula floty pełna, brak posiłków, specjalizacje", () => {
    const p = player();
    const empire = empireStats(p, TILES);
    const tips = commanderTips({
      player: p,
      players: [p],
      objectives: [],
      vpsToWin: 10,
      phase: "action",
      isTurn: false,
      agenda: null,
      empire,
    });
    const ids = tips.map((t) => t.id);
    expect(ids).toEqual(expect.arrayContaining(["fleet-pool", "depleted", "skips"]));
    expect(ids).not.toContain("no-production");
  });

  it("porada o braku PRODUCTION, gdy gracz jest na planszy bez doku", () => {
    const p = player();
    const empire = empireStats(p, { "202": TILES["202"] });
    expect(empire.maxProduction).toBe(0);
    expect(empire.build.every((b) => b.max === 0)).toBe(true);
    const tips = commanderTips({
      player: p,
      players: [p],
      objectives: [],
      vpsToWin: 10,
      phase: "action",
      isTurn: false,
      agenda: null,
      empire,
    });
    expect(tips.map((t) => t.id)).toContain("no-production");
  });
});
