/**
 * Testy czystej walidacji doboru frakcji w setupie (`validateSetup`).
 *
 * Skupienie: reguła „max 1 wariant z rodziny frakcji" po stronie UI. Council Keleres
 * ma trzy warianty mentora (keleresm/keleresx/keleresa) będące JEDNĄ frakcją, więc
 * wybór dwóch z nich przez różnych graczy jest niedozwolony — tak samo jak dwa razy ten
 * sam `faction_id` (RULES.md 28.1; backend egzekwuje to przez `faction_family`).
 */

import { describe, it, expect } from "vitest";

import {
  validateSetup,
  type SetupSlot,
  type PlayerColor,
  RANDOM_FACTION,
  AVAILABLE_COLORS,
} from "./useSetupStore";
import type { FactionInfo } from "@/api/useNewGame";

/** Minimalny slot gracza o poprawnej (unikalnej) barwie — frakcja do nadpisania. */
function slot(factionId: string, color: PlayerColor): SetupSlot {
  return {
    name: "",
    color,
    factionId,
    startingTech: [],
    controlType: "HUMAN",
    difficulty: null,
    personality: null,
  };
}

// `validateSetup` woła też walidację technologii startowych; Keleres ma odroczony
// wybór (pomijany), a dla zwykłych frakcji pusta mapa daje amount=0 (brak wymagań).
const NO_FACTION_DATA = new Map<string, FactionInfo>();

describe("validateSetup — dobór frakcji (rodzina Keleres)", () => {
  it("odrzuca dwa RÓŻNE warianty Keleres u różnych graczy", () => {
    const slots = [
      slot("keleresm", AVAILABLE_COLORS[0]),
      slot("keleresx", AVAILABLE_COLORS[1]),
    ];
    expect(validateSetup(slots, NO_FACTION_DATA)).toMatch(/duplicated/i);
  });

  it("odrzuca dwa razy ten sam wariant Keleres", () => {
    const slots = [
      slot("keleresm", AVAILABLE_COLORS[0]),
      slot("keleresm", AVAILABLE_COLORS[1]),
    ];
    expect(validateSetup(slots, NO_FACTION_DATA)).toMatch(/duplicated/i);
  });

  it("dopuszcza jeden wariant Keleres obok innej frakcji", () => {
    const slots = [
      slot("keleresm", AVAILABLE_COLORS[0]),
      slot("sol", AVAILABLE_COLORS[1]),
    ];
    expect(validateSetup(slots, NO_FACTION_DATA)).toBeNull();
  });

  it("dopuszcza Keleres obok graczy losujących frakcję", () => {
    const slots = [
      slot("keleresx", AVAILABLE_COLORS[0]),
      slot(RANDOM_FACTION, AVAILABLE_COLORS[1]),
      slot(RANDOM_FACTION, AVAILABLE_COLORS[2]),
    ];
    expect(validateSetup(slots, NO_FACTION_DATA)).toBeNull();
  });

  it("nadal odrzuca duplikat zwykłej frakcji (nie-wariantu)", () => {
    const slots = [
      slot("sol", AVAILABLE_COLORS[0]),
      slot("sol", AVAILABLE_COLORS[1]),
    ];
    expect(validateSetup(slots, NO_FACTION_DATA)).toMatch(/duplicated/i);
  });
});
