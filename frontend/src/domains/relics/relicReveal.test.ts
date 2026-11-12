import { describe, expect, it } from "vitest";
import type { RelicReveal } from "@/entities/data/types";
import { fragmentSprite, relicFaceImage, revealFragments, revealHeadline } from "./relicReveal";

const base: RelicReveal = { seq: 1, playerId: "p1", relicId: "codex", source: "fragments" };

describe("relicReveal", () => {
  it("bierze sprite fragmentu z id karty, a dżokera z typu łączenia", () => {
    expect(fragmentSprite("hrf2")).toContain("pa_fragment_hrf");
    expect(fragmentSprite("urf1", "cultural")).toContain("pa_fragment_urf");
    expect(fragmentSprite("", "industrial")).toContain("pa_fragment_irf");
  });

  it("animuje purge'owane fragmenty (3 domyślnie)", () => {
    const reveal = { ...base, fragments: ["crf1", "crf2", "urf1"], kind: "cultural" };
    expect(revealFragments(reveal)).toHaveLength(3);
    expect(revealFragments({ ...base, kind: "cultural" })[0]).toContain("pa_fragment_crf");
  });

  it("opisuje źródło w nagłówku", () => {
    const forged = revealHeadline({ ...base, fragments: ["a", "b", "c"], kind: "hazardous" }, "Sol", {});
    expect(forged.title).toBe("Sol forges a relic");
    expect(forged.subtitle).toBe("3 hazardous relic fragments were purged");
    const fracture = revealHeadline({ ...base, source: "fracture", planet: "cocytus" }, "Sol", {
      planet: "Cocytus",
    });
    expect(fracture.subtitle).toBe("Sol claimed Cocytus in The Fracture");
    const empty = revealHeadline({ ...base, relicId: null }, "Sol", {});
    expect(empty.title).toBe("Sol purges relic fragments");
  });

  it("awers to na razie placeholder", () => {
    expect(relicFaceImage("codex")).toBeNull();
  });
});
