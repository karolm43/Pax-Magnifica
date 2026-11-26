import { describe, expect, it } from "vitest";
import type { ActivityEntry, ActivityFact } from "@/api/useBoardEditor";
import { momentsForEntry, phaseSweep } from "./keyMoments";

const fact = (f: Partial<ActivityFact> & { type: string }): ActivityFact => ({
  player_id: null,
  value: null,
  delta: null,
  detail: null,
  ...f,
});

function entry(facts: ActivityFact[], kind: ActivityEntry["activity"]["kind"] = "tactical"): ActivityEntry {
  return {
    seq: 7,
    is_current: true,
    created_at: null,
    activity: {
      kind,
      action: "component.use",
      actor_id: "p1",
      target_id: null,
      subject: null,
      detail: null,
      round: 2,
      phase: "action",
      facts,
    },
  };
}

const isHero = (id: string) => id.endsWith("hero");

describe("momentsForEntry (RULES.md 64)", () => {
  it("bohater purge'owany = moment bohatera; agent/commander nie", () => {
    const e = entry([
      fact({ type: "leader", player_id: "p1", value: "arborechero", detail: "purged" }),
      fact({ type: "leader", player_id: "p1", value: "arborecagent", detail: "exhausted" }),
    ]);
    expect(momentsForEntry(e, isHero)).toEqual([
      { kind: "hero", seq: 7, player: "p1", leaderId: "arborechero" },
    ]);
  });

  it("efekt leaders:<bohater> + purge = jeden moment", () => {
    const e = entry([
      fact({ type: "effect", player_id: "p1", value: "leaders:letnevhero", detail: "round" }),
      fact({ type: "leader", player_id: "p1", value: "letnevhero", detail: "purged" }),
    ]);
    expect(momentsForEntry(e, isHero)).toEqual([
      { kind: "hero", seq: 7, player: "p1", leaderId: "letnevhero" },
    ]);
  });

  it("Nova Seed: wymieniony kafel jedzie z momentem bohatera (stary kafel do wybuchu)", () => {
    const e = entry([
      fact({ type: "tile_replaced", value: "305", detail: "26>81" }),
      fact({ type: "leader", player_id: "p1", value: "muaathero", detail: "purged" }),
    ]);
    expect(momentsForEntry(e, isHero)).toEqual([
      { kind: "hero", seq: 7, player: "p1", leaderId: "muaathero", replaced: [{ position: "305", from: "26" }] },
    ]);
  });

  it("Geoform: bohater dołączony do planety (bez purge) = moment z planetą", () => {
    const e = entry([
      fact({ type: "attached", value: "titanshero", detail: "elysium" }),
      fact({ type: "attached", value: "dmz", detail: "elysium" }),
    ]);
    expect(momentsForEntry(e, isHero)).toEqual([
      { kind: "hero", seq: 7, player: "p1", leaderId: "titanshero", planets: ["elysium"] },
    ]);
  });

  it("fakty area: miejsca działania bohatera (własne vs rywali)", () => {
    const e = entry([
      fact({ type: "leader", player_id: "p1", value: "solhero", detail: "purged" }),
      fact({ type: "area", player_id: "p1", value: "101", detail: "token_removed" }),
      fact({ type: "area", player_id: "p2", value: "102", detail: "loss" }),
    ]);
    expect(momentsForEntry(e, isHero)).toEqual([
      {
        kind: "hero",
        seq: 7,
        player: "p1",
        leaderId: "solhero",
        areas: [
          { position: "101", self: true, kind: "token_removed" },
          { position: "102", self: false, kind: "loss" },
        ],
      },
    ]);
  });

  it("odblokowanie bohatera nie jest użyciem", () => {
    const e = entry([fact({ type: "leader", player_id: "p1", value: "solhero", detail: "unlocked" })]);
    expect(momentsForEntry(e, isHero)).toEqual([]);
  });

  it("przełom przed Fracture w jednym wpisie", () => {
    const e = entry([
      fact({ type: "fracture_entered", player_id: "p2" }),
      fact({ type: "breakthrough_unlocked", player_id: "p2" }),
    ]);
    expect(momentsForEntry(e, isHero).map((m) => m.kind)).toEqual(["breakthrough", "fracture"]);
  });

  it("God-Mode: tylko Fracture", () => {
    const e = entry(
      [
        fact({ type: "fracture_entered", player_id: "p2" }),
        fact({ type: "leader", player_id: "p1", value: "solhero", detail: "purged" }),
        fact({ type: "custodians_removed" }),
      ],
      "godmode",
    );
    expect(momentsForEntry(e, isHero)).toEqual([{ kind: "fracture", seq: 7, player: "p2" }]);
  });

  it("Custodians: zdejmujący = gracz z +VP", () => {
    const e = entry([
      fact({ type: "custodians_removed" }),
      fact({ type: "vp", player_id: "p3", delta: 1 }),
    ]);
    expect(momentsForEntry(e, isHero)).toEqual([{ kind: "custodians", seq: 7, player: "p3" }]);
  });

  it("Stellar Converter: relic purged + destroyed planet = converter moment", () => {
    const e = entry([
      fact({ type: "relic", player_id: "p1", value: "stellarconverter", detail: "lost" }),
      fact({ type: "planet_destroyed", value: "lodor", detail: "205" }),
    ]);
    expect(momentsForEntry(e, isHero)).toEqual([
      { kind: "converter", seq: 7, player: "p1", planet: "lodor", position: "205" },
    ]);
  });

  it("Creuss wormhole token placed / moved = wormhole moment (position, origin)", () => {
    const placed = entry([fact({ type: "faction_token", player_id: "p1", value: "creussalpha", detail: "space", position: "205" })]);
    expect(momentsForEntry(placed, isHero)).toEqual([
      { kind: "wormhole", seq: 7, player: "p1", token: "creussalpha", position: "205", from: null },
    ]);
    const moved = entry([
      fact({ type: "faction_token", player_id: "p1", value: "creussbeta", detail: "space", position: "301" }),
      fact({ type: "faction_token_removed", player_id: "p1", value: "creussbeta", detail: "space", position: "205" }),
    ]);
    expect(momentsForEntry(moved, isHero)).toEqual([
      { kind: "wormhole", seq: 7, player: "p1", token: "creussbeta", position: "301", from: "205" },
    ]);
    // Sleeper tokens (Titans) are not wormholes.
    const sleeper = entry([fact({ type: "faction_token", player_id: "p1", value: "sleeper", detail: "wellon", position: "205" })]);
    expect(momentsForEntry(sleeper, isHero)).toEqual([]);
  });

  it("Singularity Reactor: hero moment with BOTH swapped tiles, no wormhole moment", () => {
    const e = entry([
      fact({ type: "leader", player_id: "p1", value: "ghosthero", detail: "purged" }),
      fact({ type: "tile_replaced", value: "102", detail: "26>01" }),
      fact({ type: "tile_replaced", value: "105", detail: "01>26" }),
      fact({ type: "faction_token", player_id: "p1", value: "creussgamma", detail: "space", position: "105" }),
      fact({ type: "faction_token_removed", player_id: "p1", value: "creussgamma", detail: "space", position: "102" }),
    ]);
    const moments = momentsForEntry(e, isHero);
    expect(moments).toHaveLength(1);
    expect(moments[0]).toMatchObject({
      kind: "hero",
      leaderId: "ghosthero",
      replaced: [
        { position: "102", from: "26" },
        { position: "105", from: "01" },
      ],
    });
  });

  it("The Silver Flame destroying a home system is not the converter moment", () => {
    const e = entry([
      fact({ type: "relic", player_id: "p1", value: "thesilverflame", detail: "lost" }),
      fact({ type: "planet_destroyed", value: "jord", detail: "103" }),
    ]);
    expect(momentsForEntry(e, isHero)).toEqual([]);
  });
});

describe("phaseSweep", () => {
  it("brak zmiany fazy = brak paska", () => {
    expect(phaseSweep({ phase: "action", round: 2 }, { phase: "action", round: 2 })).toBeNull();
  });

  it("faza strategii = nowa runda", () => {
    expect(phaseSweep({ phase: "agenda", round: 2 }, { phase: "strategy", round: 3 })).toEqual({
      id: "round-3-strategy",
      variant: "round",
      title: "Round 3",
      subtitle: "Strategy Phase",
    });
  });

  it("zwykła faza: nazwa + runda", () => {
    expect(phaseSweep({ phase: "strategy", round: 3 }, { phase: "action", round: 3 })).toMatchObject({
      variant: "action",
      title: "Action Phase",
      subtitle: "Round 3",
    });
  });

  it("faza bez paska (setup, finished)", () => {
    expect(phaseSweep({ phase: "agenda", round: 9 }, { phase: "finished", round: 9 })).toBeNull();
  });
});
