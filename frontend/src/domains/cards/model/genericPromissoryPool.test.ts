import { describe, expect, it } from "vitest";
import { genericPromissoryPool } from "./cardPoolBrowser";

describe("genericPromissoryPool (biblioteka komponentów)", () => {
  it("pięć ogólnych notek z oficjalnych źródeł, bez surowego znacznika <color>", () => {
    const [group] = genericPromissoryPool();
    const names = group.entries.map((e) => e.name);
    expect(names).toEqual([
      "Alliance",
      "Ceasefire",
      "Political Secret",
      "Support for the Throne",
      "Trade Agreement",
    ]);
    for (const entry of group.entries) {
      expect(entry.text).not.toContain("<color>");
      expect(entry.text).toContain("[color]");
    }
  });
});
