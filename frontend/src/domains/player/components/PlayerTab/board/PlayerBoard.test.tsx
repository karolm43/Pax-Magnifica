import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PlayerData } from "@/entities/data/types";
import { getUnitData } from "@/entities/lookup/units";
import type { Tile } from "@/entities/game/types";
import { empireStats } from "../empireStats";
import { PlayerBoard } from "./PlayerBoard";
import { dockProductionTip, unitProductionTip } from "./productionTips";
import { statBoxes, unitKeywords, upgradeStrip } from "./sheetUnits";

vi.mock("@/state/useGameContext", () => ({
  useGameContext: () => undefined,
  useGameData: () => undefined,
  useDecalOverrides: () => ({ decalOverrides: {} }),
}));

const unit = (id: string) => getUnitData(id)!;

const muaat = (patch: Partial<PlayerData> = {}) =>
  ({
    discordId: "p1",
    color: "red",
    faction: "muaat",
    displayName: "Umbat",
    abilities: ["star_forge", "gashlai_physiology"],
    unitsOwned: [
      "muaat_flagship", "muaat_warsun", "muaat_mech", "cruiser", "dreadnought", "destroyer",
      "pds", "carrier2", "fighter", "infantry", "spacedock",
    ],
    unitCounts: { gf: { deployedCount: 4, unitCap: 12 }, fs: { deployedCount: 0, unitCap: 1 } },
    leaders: [
      { id: "muaatagent", type: "agent", exhausted: true, locked: false, tgCount: 0, active: false },
      { id: "muaatcommander", type: "commander", exhausted: false, locked: true, tgCount: 0, active: false },
      { id: "muaathero", type: "hero", exhausted: false, locked: false, purged: true, tgCount: 0, active: false },
    ],
    leaderIDs: ["muaatagent", "muaatcommander", "muaathero"],
    tacticalCC: 3,
    fleetCC: 4,
    strategicCC: 2,
    ccReinf: 7,
    tg: 5,
    commodities: 1,
    commoditiesTotal: 4,
    planets: [],
    exhaustedPlanets: [],
    resources: 0, totResources: 0, influence: 0, totInfluence: 0,
    optimalResources: 0, totOptimalResources: 0, optimalInfluence: 0, totOptimalInfluence: 0,
    flexValue: 0, totFlexValue: 0,
    ...patch,
  }) as unknown as PlayerData;

/** Home system: 4 destroyers (fleet pool 4 is full), PRODUCTION 5 for red. */
const HOME: Record<string, Tile> = {
  "000": {
    position: "000",
    unitsByFaction: { muaat: [{ entityId: "dd", entityType: "unit", count: 4 }] },
    planets: { muaat: { controlledBy: "muaat", unitsByFaction: {} } },
    productionByColor: { red: 5 },
  } as unknown as Tile,
};

const board = (patch: Partial<PlayerData> = {}, tiles: Record<string, Tile> = HOME) => {
  const player = muaat(patch);
  return <PlayerBoard player={player} empire={empireStats(player, tiles)} />;
};

describe("sheetUnits: what a unit box prints", () => {
  it("keeps only the stat boxes of the printed sheet", () => {
    const labels = (id: string) => statBoxes(unit(id)).map((s) => s.label);
    expect(labels("cruiser")).toEqual(["Cost", "Combat", "Move", "Capacity"]);
    expect(labels("destroyer")).toEqual(["Cost", "Combat", "Move"]);
    expect(labels("infantry")).toEqual(["Cost", "Combat"]);
    expect(labels("spacedock")).toEqual([]);
    expect(labels("pds")).toEqual([]);
    expect(statBoxes(unit("infantry"))[0]).toEqual({ label: "Cost", value: "1", times: 2 });
  });

  it("spells out the keywords from unit data", () => {
    expect(unitKeywords(unit("muaat_warsun"))).toEqual(["Sustain Damage", "Bombardment 3 (x3)"]);
    expect(unitKeywords(unit("spacedock"))).toEqual(["Production X"]);
  });

  it("marks the upgrade strip as researched on the upgraded unit", () => {
    expect(upgradeStrip(unit("carrier"))?.researched).toBe(false);
    expect(upgradeStrip(unit("carrier2"))?.researched).toBe(true);
    expect(upgradeStrip(unit("mech"))).toBeNull();
  });
});

describe("PlayerBoard", () => {
  it("lays out leaders with their live state and the mech", () => {
    render(board());
    const wing = within(screen.getByRole("region", { name: "Leaders and mech" }));
    expect(wing.getByRole("button", { name: "Umbat, agent, exhausted" })).toBeInTheDocument();
    expect(wing.getByRole("button", { name: "Magmus, commander, locked" })).toHaveTextContent(
      "Produce a war sun.",
    );
    expect(wing.getByRole("button", { name: /, hero, purged$/ })).toBeInTheDocument();
    expect(wing.getByRole("button", { name: /^Ember Colossus, 0 of 4 deployed/ })).toBeInTheDocument();
  });

  it("prints the faction sheet: flagship, units with counts, abilities, commodities", () => {
    render(board());
    const sheet = within(screen.getByRole("region", { name: /faction sheet$/ }));
    expect(sheet.getByRole("button", { name: "The Inferno, 0 of 1 deployed" })).toBeInTheDocument();
    expect(sheet.getByRole("button", { name: "Infantry I, 4 of 12 deployed" })).toBeInTheDocument();
    expect(sheet.getByRole("button", { name: /^Carrier II,/ })).toHaveTextContent("Upgraded");
    expect(sheet.getByRole("region", { name: "Faction abilities" })).toHaveTextContent(/star forge/i);
    expect(sheet.getByLabelText("1 of 4 commodities")).toHaveTextContent("1 / 4");
  });

  it("shows an empty War Sun box when the player has none", () => {
    render(board({ faction: "sol", unitsOwned: ["carrier"] }, {}));
    expect(screen.getByRole("article", { name: "War Sun" })).toHaveTextContent(
      "Requires War Sun technology",
    );
  });

  it("shows the command pools, trade goods and a full fleet pool warning", () => {
    render(board());
    const wing = within(screen.getByRole("region", { name: "Command sheet" }));
    expect(wing.getByRole("group", { name: "Tactic pool: 3 command tokens" })).toBeInTheDocument();
    expect(wing.getByRole("group", { name: "Strategy pool: 2 command tokens" })).toBeInTheDocument();
    expect(wing.getByRole("group", { name: "Trade goods: 5" })).toBeInTheDocument();
    expect(wing.getByRole("group", { name: "Fleet pool: 4 command tokens" })).toHaveTextContent(
      "Largest 4/4",
    );
    expect(wing.getByLabelText("Fleet pool full")).toBeInTheDocument();
  });

  it("prints under each silhouette what can be produced right now", () => {
    render(board({ resources: 6, tg: 0, planets: [] }));
    const sheet = within(screen.getByRole("region", { name: /faction sheet$/ }));
    // Fleet pool 4 already holds 4 ships at the only dock: ships are blocked, fighters are not.
    expect(sheet.getByRole("button", { name: /^Dreadnought/ })).toHaveTextContent("Can't buildfleet pool full (4/4)");
    expect(sheet.getByRole("button", { name: /^Fighter/ })).toHaveTextContent("Can build 5Muaat produces 5");
    expect(sheet.getByRole("button", { name: /^Space Dock/ })).toHaveTextContent("Produces up to 5in Muaat");
  });

  it("leaves the production lines out without board data", () => {
    render(<PlayerBoard player={muaat()} />);
    expect(screen.queryByText(/Can build|Produces up to/)).not.toBeInTheDocument();
  });
});

describe("productionTips", () => {
  const empire = (patch: Partial<PlayerData> = {}, tiles: Record<string, Tile> = HOME) =>
    empireStats(muaat(patch), tiles);
  const option = (e: ReturnType<typeof empire>, id: string) => e.build.find((b) => b.asyncId === id)!;

  it("names the limit when the unit can be built", () => {
    const e = empire({ resources: 2, tg: 0, planets: [] });
    expect(unitProductionTip(option(e, "ff"), e)).toMatchObject({
      tone: "ok",
      title: "Can build 4",
      reason: "2 resources to spend",
    });
  });

  it("says why a unit cannot be built", () => {
    const poor = empire({ resources: 0, tg: 1, planets: [] });
    expect(unitProductionTip(option(poor, "dn"), poor)).toMatchObject({
      tone: "blocked",
      title: "Can't afford",
      reason: "costs 4 · you have 1",
    });
    const noDock = empire({ resources: 9 }, {});
    expect(unitProductionTip(option(noDock, "ff"), noDock).reason).toBe("no space dock on the board");
    expect(dockProductionTip(noDock).tone).toBe("blocked");
  });

  it("lists every system with PRODUCTION, best first", () => {
    const tiles = {
      ...HOME,
      "101": { position: "101", unitsByFaction: { muaat: [{ entityId: "sd", entityType: "unit", count: 1 }] }, planets: {}, productionByColor: { red: 2 } } as unknown as Tile,
    };
    const tip = dockProductionTip(empire({}, tiles));
    expect(tip).toMatchObject({ title: "Produces up to 5", reason: "in Muaat · +1 system" });
    expect(tip.detail).toContain("System 101 2");
  });
});
