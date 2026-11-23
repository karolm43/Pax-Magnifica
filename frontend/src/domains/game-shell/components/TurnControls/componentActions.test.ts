import { describe, expect, it, vi } from "vitest";
import type { PlayerData } from "@/entities/data/types";
import { collectComponentActions } from "./componentActions";

// Dane statyczne podmienione: każdy komponent ma nagłówek „ACTION”.
vi.mock("@/entities/lookup/leaders", () => ({
  getLeaderById: (id: string) => ({ id, name: `Leader ${id}`, abilityWindow: "ACTION", abilityText: "" }),
}));
vi.mock("@/entities/lookup/tech", () => ({
  getTechData: (id: string) => ({ name: `Tech ${id}`, text: "ACTION: Do it." }),
}));
vi.mock("@/entities/lookup/relics", () => ({
  getRelicData: (id: string) => ({ name: `Relic ${id}`, text: "ACTION: Purge this card." }),
}));
vi.mock("@/entities/lookup/breakthroughs", () => ({
  getBreakthroughData: (id: string) => ({ name: `BT ${id}`, text: "ACTION: Exhaust this card." }),
}));
vi.mock("@/entities/lookup/abilities", () => ({
  getAbility: (id: string) => ({ name: `Ability ${id}` }),
  getAbilityKind: () => "action",
}));

function player(extra: Partial<PlayerData>): PlayerData {
  return { abilities: [], leaderIDs: [], techs: [], relics: [], ...extra } as unknown as PlayerData;
}

describe("collectComponentActions - dostępność", () => {
  it("wyczerpane, zablokowane i zużyte komponenty mają powód, gotowe - nie", () => {
    const choices = collectComponentActions(
      player({
        abilities: ["ab"],
        leaderIDs: ["agent", "hero", "spent", "ready"],
        leaders: [
          { id: "agent", exhausted: true, locked: false },
          { id: "hero", exhausted: false, locked: true },
          { id: "spent", exhausted: false, locked: false, purged: true },
          { id: "ready", exhausted: false, locked: false },
        ] as PlayerData["leaders"],
        techs: ["t1", "t2"],
        exhaustedTechs: ["t1"],
        relics: ["r1"],
        exhaustedRelics: ["r1"],
        breakthrough: { breakthroughId: "bt", unlocked: true, exhausted: true, tradeGoodsStored: 0 },
        legendaryAbilities: [{ planet: "p", name: "Legend", text: "", kind: "action", exhausted: true }],
      }),
      [],
    );
    const reason = Object.fromEntries(choices.map((c) => [`${c.kind}:${c.id}`, c.unavailable]));
    expect(reason).toEqual({
      "ability:ab": undefined,
      "leader:agent": "Exhausted",
      "leader:hero": "Locked",
      "leader:spent": "Purged",
      "leader:ready": undefined,
      "technology:t1": "Exhausted",
      "technology:t2": undefined,
      "relic:r1": "Exhausted",
      "breakthrough:bt": "Exhausted",
      "legendary:p": "Exhausted",
    });
  });
});
