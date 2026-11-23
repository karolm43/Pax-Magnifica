import { describe, expect, it } from "vitest";
import type { Activity, ActivityEntry, ActivityFact } from "@/api/useBoardEditor";
import { buildChronicle } from "./buildChronicle";

const players = {
  p1: { faction: "sol", color: "blue", display_name: "Ann", is_bot: false, faction_name: "The Federation of Sol" },
  p2: { faction: "hacan", color: "red", display_name: "Bob", is_bot: false, faction_name: "The Emirates of Hacan" },
};

let seq = 0;
function entry(partial: Partial<Activity>): ActivityEntry {
  seq += 1;
  return {
    seq,
    is_current: false,
    created_at: null,
    activity: {
      kind: "misc",
      action: "update",
      actor_id: null,
      target_id: null,
      subject: null,
      detail: null,
      round: 1,
      phase: "action",
      facts: [],
      ...partial,
    },
  };
}

const fact = (f: Partial<ActivityFact> & { type: string }): ActivityFact => ({
  player_id: null,
  value: null,
  detail: null,
  delta: null,
  ...f,
});

const names = { systemName: (pos: string) => `System ${pos}` };

describe("buildChronicle", () => {
  it("opisuje bitwę lorem i suchymi faktami", () => {
    const entries = [
      entry({
        kind: "combat",
        action: "combat.end",
        actor_id: "p1",
        target_id: "p2",
        subject: "space",
        detail: "101",
        facts: [
          fact({ type: "battle_result", player_id: "p1", detail: "winner", delta: 2 }),
          fact({ type: "units", player_id: "p2", value: "fighter", delta: -3 }),
        ],
      }),
    ];
    const [chapter] = buildChronicle({ entries, players, currentSeq: null }, names);
    const battle = chapter.entries.find((e) => e.kind === "battle");
    expect(battle?.text).toContain("System 101");
    expect(battle?.facts.join(" ")).toContain("Winner: The Federation of Sol");
    expect(battle?.facts.join(" ")).toContain("3 Fighter");
    expect(battle?.actors).toEqual(["p1", "p2"]);
  });

  it("rozróżnia podbój od kolonizacji", () => {
    const entries = [
      entry({
        facts: [
          fact({ type: "planet_gained", player_id: "p1", value: "mecatol" }),
          fact({ type: "planet_lost", player_id: "p2", value: "mecatol" }),
          fact({ type: "planet_gained", player_id: "p1", value: "lodor" }),
        ],
      }),
    ];
    const [chapter] = buildChronicle({ entries, players, currentSeq: null }, names);
    const kinds = chapter.entries.map((e) => e.kind).filter((k) => k !== "prologue");
    expect(kinds).toEqual(["conquest", "settle"]);
  });

  it("pomija cofnięte wpisy i God-Mode, a rozdziały idą po rundach ze stanem wyścigu", () => {
    const entries = [
      entry({ round: 1, facts: [fact({ type: "vp", player_id: "p1", delta: 2 }), fact({ type: "relic", player_id: "p1", value: "x" })] }),
      entry({ round: 2, facts: [fact({ type: "tech", player_id: "p2", value: "ps" })] }),
      entry({ kind: "godmode", action: "godmode.edit", round: 2, facts: [fact({ type: "tech", player_id: "p2", value: "zz" })] }),
      entry({ round: 3, facts: [fact({ type: "tech", player_id: "p2", value: "undone" })] }),
    ];
    const chapters = buildChronicle({ entries, players, currentSeq: entries[2].seq }, names);
    expect(chapters.map((c) => c.round)).toEqual([1, 2]);
    expect(chapters[0].standings[0]).toEqual({ playerId: "p1", vp: 2 });
    expect(chapters[0].closing).toContain("2 points");
    expect(chapters[1].entries.filter((e) => e.kind === "tech")).toHaveLength(1);
    expect(chapters[1].entries[0].minor).toBe(true);
  });

  it("jest deterministyczna: ten sam feed daje ten sam tekst", () => {
    const entries = [entry({ facts: [fact({ type: "relic", player_id: "p1", value: "r" })] })];
    const a = buildChronicle({ entries, players, currentSeq: null }, names);
    const b = buildChronicle({ entries, players, currentSeq: null }, names);
    expect(a).toEqual(b);
    expect(a[0].entries.some((e) => e.kind === "relic")).toBe(true);
  });

  it("zdanie otwierające rundę nawiązuje do poprzedniej i ma innego kronikarza", () => {
    const entries = [
      entry({
        round: 1,
        kind: "combat",
        action: "combat.end",
        actor_id: "p1",
        target_id: "p2",
        subject: "space",
        detail: "101",
        facts: [fact({ type: "battle_result", player_id: "p1", detail: "winner", delta: 2 })],
      }),
      entry({ round: 2, facts: [fact({ type: "relic", player_id: "p2", value: "x" })] }),
      entry({ round: 3, facts: [fact({ type: "tech", player_id: "p1", value: "ps" })] }),
    ];
    const [r1, r2, r3] = buildChronicle({ entries, players, currentSeq: null }, names);
    expect(r1.opener.text).toMatch(/throne|Emperor/);
    expect(r2.opener.text).toMatch(/System 101|Federation|Hacan|battle/);
    expect(r3.opener.text).toContain("The Emirates of Hacan");
    expect(new Set([r1, r2, r3].map((c) => c.opener.author)).size).toBe(3);
  });
});

