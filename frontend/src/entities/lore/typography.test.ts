import { describe, expect, it } from "vitest";
import { attribution, NBSP, quoted, typeset, WORD_JOINER } from "./typography";

describe("typeset", () => {
  it("zamienia proste cudzysłowy i apostrofy na drukarskie", () => {
    expect(typeset('He said "no" and left')).toBe("He said “no” and left");
    expect(typeset("the Emperor's will")).toBe("the Emperor’s will");
    expect(typeset("'quoted' text")).toBe("‘quoted’ text");
  });

  it("zamienia -- i ... oraz wiąże myślnik z poprzednim słowem", () => {
    expect(typeset("Wait -- what...")).toBe(`Wait${NBSP}— what…`);
    expect(typeset("End — begin")).toBe(`End${NBSP}— begin`);
  });

  it("wiąże jednoliterowe słowa z następnym", () => {
    expect(typeset("a ship and I left")).toBe(`a${NBSP}ship and I${NBSP}left`);
  });

  it("jest idempotentna", () => {
    const once = typeset('A "test" -- of it’s...');
    expect(typeset(once)).toBe(once);
  });
});

describe("quoted / attribution", () => {
  it("opakowuje cytat i skleja zamykający cudzysłów z ostatnim słowem", () => {
    expect(quoted("Hold the line.")).toBe(`“Hold the line.${WORD_JOINER}”`);
  });

  it("zdejmuje cudzysłowy z brzegów danych", () => {
    expect(quoted('"Hold the line."')).toBe(quoted("Hold the line."));
  });

  it("podpis ma myślnik z twardą spacją i nie dubluje kreski", () => {
    expect(attribution("Sol")).toBe(`—${NBSP}Sol`);
    expect(attribution("— Sol")).toBe(attribution("Sol"));
  });
});
