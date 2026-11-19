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
  assignPreferredColors,
  resolveRandomFactions,
  toNewGameRequest,
  useSetupStore,
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
    seat: AVAILABLE_COLORS.indexOf(color),
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

describe("kolory i miejsca", () => {
  const factions = new Map<string, FactionInfo>([
    ["sol", { id: "sol", preferred_colours: ["blu", "azr"] } as FactionInfo],
    ["hacan", { id: "hacan", preferred_colours: ["blu", "org"] } as FactionInfo],
  ]);

  it("paleta zawiera kolory specjalne i split", () => {
    expect(AVAILABLE_COLORS).toEqual(expect.arrayContaining(["rbw", "splitred", "nea"]));
    expect(new Set(AVAILABLE_COLORS).size).toBe(AVAILABLE_COLORS.length);
  });

  it("assignPreferredColors daje pierwszy wolny kolor preferowany i bez duplikatów", () => {
    const slots = [slot("sol", "red"), slot("hacan", "grn"), slot(RANDOM_FACTION, "blu")];
    const result = assignPreferredColors(slots, factions);
    expect(result.map((s) => s.color)).toEqual(["blu", "org", expect.any(String)]);
    expect(new Set(result.map((s) => s.color)).size).toBe(3);
    // Gracz z losową frakcją traci zajęty kolor, ale dostaje wolny.
    expect(result[2].color).not.toBe("blu");
    expect(result[2].color).not.toBe("org");
  });

  it("swapSeat zamienia miejsca zamiast tworzyć duplikat", () => {
    useSetupStore.getState().reset();
    useSetupStore.getState().swapSeat(0, 3);
    const seats = useSetupStore.getState().slots.map((s) => s.seat);
    expect(seats[0]).toBe(3);
    expect(seats[3]).toBe(0);
    expect(new Set(seats).size).toBe(seats.length);
  });

  it("odrzuca zduplikowane miejsca", () => {
    const a = slot("sol", "red");
    const b = { ...slot("hacan", "blu"), seat: a.seat };
    expect(validateSetup([a, b], NO_FACTION_DATA)).toMatch(/seat/i);
  });

  it("toNewGameRequest wysyła home_position wybranego miejsca", () => {
    const a = { ...slot("sol", "red"), seat: 2 };
    const request = toNewGameRequest([a], "", NO_FACTION_DATA, ["301", "304", "307"]);
    expect(request.players[0].home_position).toBe("307");
    expect(request.players[0].color).toBe("red");
  });
});

describe("resolveRandomFactions", () => {
  const f = (id: string, extra: Partial<FactionInfo> = {}) =>
    ({ id, starting_tech_amount: 0, starting_tech_options: [], ...extra }) as FactionInfo;
  const pool = [
    f("sol"),
    f("hacan"),
    f("winnu", { starting_tech_amount: 1, starting_tech_options: ["a", "b", "c"] }),
    f("keleresm"),
    f("keleresx"),
  ];

  it("losuje unikalne frakcje bez ruszania jawnych wyborów", () => {
    const slots = [slot("sol", "red"), slot(RANDOM_FACTION, "blu"), slot(RANDOM_FACTION, "grn")];
    const out = resolveRandomFactions(slots, pool, () => 0);
    expect(out[0].factionId).toBe("sol");
    const ids = out.map((s) => s.factionId);
    expect(ids).not.toContain(RANDOM_FACTION);
    expect(new Set(ids).size).toBe(3);
  });

  it("losuje technologie startowe frakcji z wyborem", () => {
    const out = resolveRandomFactions([slot(RANDOM_FACTION, "red")], [pool[2]], () => 0);
    expect(out[0].factionId).toBe("winnu");
    expect(out[0].startingTech).toEqual(["a"]);
  });

  it("nie bierze dwóch wariantów Keleres", () => {
    const slots = [slot(RANDOM_FACTION, "red"), slot(RANDOM_FACTION, "blu")];
    const out = resolveRandomFactions(slots, [pool[3], pool[4]], () => 0);
    expect(out[0].factionId).toBe("keleresm");
    expect(out[1].factionId).toBe(RANDOM_FACTION);
  });

  it("najpierw losuje frakcje zrobione w silniku, potem resztę", () => {
    const factions = [f("sol"), f("hacan", { implemented: true }), f("winnu")];
    const slots = [slot(RANDOM_FACTION, "red"), slot(RANDOM_FACTION, "blu")];
    const out = resolveRandomFactions(slots, factions, () => 0);
    expect(out[0].factionId).toBe("hacan");
    expect(out[1].factionId).toBe("sol");
  });
});