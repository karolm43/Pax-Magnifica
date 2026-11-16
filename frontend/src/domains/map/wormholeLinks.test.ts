import { describe, expect, it } from "vitest";
import type { Tile } from "@/entities/game/types";
import { getTokenRule } from "./components/SystemDossier/featureRules";
import { getPrintedLinkPoints } from "./components/layers/WormholeBlockedLayer";
import { linkKindsOfToken, linkTargets } from "./wormholeLinks";

function tile(position: string, systemId: string, tokens: string[] = []): Tile {
  return { position, systemId, tokens } as unknown as Tile;
}

describe("wormholeLinks", () => {
  const tiles = [
    tile("101", "26"), // Lodor: nadruk alfa
    tile("202", "39"), // pusty system z alfą
    tile("303", "40"), // pusty system z betą
    tile("404", "19", ["gamma"]),
    tile("505", "20", ["gamma"]),
    tile("606", "21", ["ingress"]),
    tile("frac2", "fracture2"), // egress nadrukowany
    tile("frac6", "fracture6"),
  ];

  it("wormhole prowadzi do systemów z tym samym typem (nadruk i żeton)", () => {
    expect(linkTargets("ALPHA", "101", tiles)).toEqual(["202"]);
    expect(linkTargets("GAMMA", "404", tiles)).toEqual(["505"]);
    expect(linkTargets("BETA", "303", tiles)).toEqual([]);
  });

  it("ingress prowadzi do każdego egress i odwrotnie", () => {
    expect(linkTargets("INGRESS", "606", tiles)).toEqual(["frac2", "frac6"]);
    expect(linkTargets("EGRESS", "frac2", tiles)).toEqual(["606"]);
  });

  it("rozpoznaje żetony łączące i nadruki na kafelkach", () => {
    expect(linkKindsOfToken("gamma")).toEqual(["GAMMA"]);
    expect(linkKindsOfToken("ingress")).toEqual(["INGRESS"]);
    expect(linkKindsOfToken("frontier")).toEqual([]);
    expect(getPrintedLinkPoints("26").map((p) => p.kinds)).toEqual([["ALPHA"]]);
    expect(getPrintedLinkPoints("fracture2").map((p) => p.kinds)).toEqual([["EGRESS"]]);
  });

  it("żeton wormhole ma opis reguły (dymek na mapie)", () => {
    expect(getTokenRule("gamma")?.name).toBe("Gamma Wormhole");
  });
});
