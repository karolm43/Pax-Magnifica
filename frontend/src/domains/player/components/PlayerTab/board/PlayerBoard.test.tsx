import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PlayerData } from "@/entities/data/types";
import { getUnitData } from "@/entities/lookup/units";
import { PlayerBoard } from "./PlayerBoard";
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
    ...patch,
  }) as unknown as PlayerData;

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
    render(<PlayerBoard player={muaat()} largestFleet={4} />);
    const wing = within(screen.getByRole("region", { name: "Leaders and mech" }));
    expect(wing.getByRole("button", { name: "Umbat, agent, exhausted" })).toBeInTheDocument();
    expect(wing.getByRole("button", { name: "Magmus, commander, locked" })).toHaveTextContent(
      "Produce a war sun.",
    );
    expect(wing.getByRole("button", { name: /, hero, purged$/ })).toBeInTheDocument();
    expect(wing.getByRole("button", { name: /^Ember Colossus, 0 of 4 deployed/ })).toBeInTheDocument();
  });

  it("prints the faction sheet: flagship, units with counts, abilities, commodities", () => {
    render(<PlayerBoard player={muaat()} largestFleet={4} />);
    const sheet = within(screen.getByRole("region", { name: /faction sheet$/ }));
    expect(sheet.getByRole("button", { name: "The Inferno, 0 of 1 deployed" })).toBeInTheDocument();
    expect(sheet.getByRole("button", { name: "Infantry I, 4 of 12 deployed" })).toBeInTheDocument();
    expect(sheet.getByRole("button", { name: /^Carrier II,/ })).toHaveTextContent("Upgraded");
    expect(sheet.getByRole("region", { name: "Faction abilities" })).toHaveTextContent(/star forge/i);
    expect(sheet.getByLabelText("1 of 4 commodities")).toHaveTextContent("1 / 4");
  });

  it("shows an empty War Sun box when the player has none", () => {
    render(<PlayerBoard player={muaat({ faction: "sol", unitsOwned: ["carrier"] })} largestFleet={0} />);
    expect(screen.getByRole("article", { name: "War Sun" })).toHaveTextContent(
      "Requires War Sun technology",
    );
  });

  it("shows the command pools, trade goods and a full fleet pool warning", () => {
    render(<PlayerBoard player={muaat()} largestFleet={4} />);
    const wing = within(screen.getByRole("region", { name: "Command sheet" }));
    expect(wing.getByRole("group", { name: "Tactic pool: 3 command tokens" })).toBeInTheDocument();
    expect(wing.getByRole("group", { name: "Strategy pool: 2 command tokens" })).toBeInTheDocument();
    expect(wing.getByRole("group", { name: "Trade goods: 5" })).toBeInTheDocument();
    expect(wing.getByRole("group", { name: "Fleet pool: 4 command tokens" })).toHaveTextContent(
      "Largest 4/4",
    );
    expect(wing.getByLabelText("Fleet pool full")).toBeInTheDocument();
  });
});
