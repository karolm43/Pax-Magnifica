import { describe, expect, it } from "vitest";
import { autoAlloc } from "./autoAlloc";

describe("autoAlloc — „Auto” rozdziału żetonów w fazie statusu", () => {
  it("nowe żetony idą do puli taktycznej, gdy flota mieści się w puli", () => {
    expect(autoAlloc({ t: 2, f: 3, s: 2 }, 2, { "101": 3 })).toEqual({ t: 4, f: 3, s: 2 });
  });

  it("najpierw dopełnia pulę floty do największej floty", () => {
    expect(autoAlloc({ t: 1, f: 3, s: 2 }, 2, { "101": 4, "202": 2 })).toEqual({
      t: 2,
      f: 4,
      s: 2,
    });
  });

  it("nie przydziela więcej, niż zdobyto", () => {
    expect(autoAlloc({ t: 0, f: 2, s: 1 }, 2, { "101": 7 })).toEqual({ t: 0, f: 4, s: 1 });
  });

  it("bez statków i bez nowych żetonów nic nie zmienia", () => {
    expect(autoAlloc({ t: 3, f: 3, s: 2 }, 0, {})).toEqual({ t: 3, f: 3, s: 2 });
  });
});
