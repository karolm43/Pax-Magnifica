import { describe, expect, it } from "vitest";
import { humanHandOwners, timingPhrase } from "./handReactions";

describe("timingPhrase", () => {
  it("bierze okno sprzed dwukropka", () => {
    expect(timingPhrase("At the start of an invasion combat: Apply +1 to the result")).toBe(
      "At the start of an invasion combat",
    );
  });

  it("bez okna (brak dwukropka albo bardzo długi wstęp) - null", () => {
    expect(timingPhrase("Gain 2 trade goods.")).toBeNull();
    expect(timingPhrase(`${"x".repeat(200)}: y`)).toBeNull();
    expect(timingPhrase(undefined)).toBeNull();
  });
});

describe("humanHandOwners", () => {
  const players = { p1: { is_bot: false }, p2: { is_bot: true }, p3: { is_bot: false } };

  it("lokalnie: ręce wszystkich ludzi, bez botów", () => {
    expect(humanHandOwners({ network: false, player_id: null }, players)).toEqual(["p1", "p3"]);
  });

  it("gra sieciowa: tylko moja ręka", () => {
    expect(humanHandOwners({ network: true, player_id: "p3" }, players)).toEqual(["p3"]);
    expect(humanHandOwners({ network: true, player_id: null }, players)).toEqual([]);
  });
});
