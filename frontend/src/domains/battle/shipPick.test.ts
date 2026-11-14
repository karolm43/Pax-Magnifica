/*
 * Decyzje „wskaż okręt" w oknie bitwy: obie strony mogą decydować naraz (np. obie mają
 * Assault Cannon) — każda dostaje SWOJĄ ofertę, nie tylko pierwsza z listy.
 */
import { describe, expect, it } from "vitest";
import type { OfferView } from "@/api/useOffers";
import { shipPickOffers } from "./shipPick";

function asc(id: string, decider: string, units: string[]): OfferView {
  return {
    id,
    player_id: decider,
    name: "Assault Cannon",
    inputs: [
      {
        key: "ship",
        kind: "choice",
        label: "Your ship to destroy",
        options: units.map((u) => ({ id: u, value: u, label: u, meta: { unit: u, player: decider } })),
      },
    ],
  } as unknown as OfferView;
}

describe("shipPickOffers", () => {
  it("obie strony walki dostają swoją decyzję jednocześnie", () => {
    const picks = shipPickOffers(
      [asc("of1", "p5", ["carrier", "cruiser"]), asc("of2", "p4", ["dreadnought", "warsun"])],
      ["p4", "p5"],
    );
    expect(picks.get("p5")?.id).toBe("of1");
    expect(picks.get("p4")?.id).toBe("of2");
  });

  it("pomija graczy spoza walki i bierze pierwszą ofertę gracza", () => {
    const picks = shipPickOffers(
      [asc("of1", "p4", ["dreadnought"]), asc("of2", "p4", ["warsun"]), asc("of3", "p9", ["carrier"])],
      ["p4", "p5"],
    );
    expect([...picks.keys()]).toEqual(["p4"]);
    expect(picks.get("p4")?.id).toBe("of1");
  });
});
