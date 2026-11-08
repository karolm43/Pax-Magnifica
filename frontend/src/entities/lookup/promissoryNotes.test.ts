import { describe, expect, it } from "vitest";
import type { FactionColorMap } from "@/entities/game/types";
import { getPromissoryNoteData } from "./promissoryNotes";

// FAN-AGENDAS: w grze Absol backend rozdaje `absol_<kolor>_ps` zamiast `<kolor>_ps`.
const colors = { red: { faction: "sol" } } as unknown as FactionColorMap;

describe("getPromissoryNoteData", () => {
  it("rozpoznaje Absol's Political Secret danego koloru", () => {
    const data = getPromissoryNoteData("absol_red_ps", colors);
    expect(data?.noteData.name).toBe("Absol's Political Secret");
    expect(data?.noteData.source).toBe("absol");
    expect(data?.faction).toBe("sol");
    expect(data?.color).toBe("red");
  });

  it("oficjalny Political Secret dalej działa", () => {
    const data = getPromissoryNoteData("red_ps", colors);
    expect(data?.noteData.alias).toBe("<color>_ps");
    expect(data?.faction).toBe("sol");
  });
});
