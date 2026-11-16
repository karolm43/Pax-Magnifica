/*
 * Decyzje „wskaż okręt" w oknie bitwy: obie strony mogą decydować naraz (np. obie mają
 * Assault Cannon) — każda dostaje SWOJĄ ofertę, nie tylko pierwsza z listy.
 */
import { describe, expect, it } from "vitest";
import type { OfferView } from "@/api/useOffers";
import { optionMatchesShip, shipPickOffers, shipPickSteps } from "./shipPick";
import { assignableShips, type ShipEntity } from "./battleAssign";

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

function devotion(): OfferView {
  const opt = (unit: string, player: string, damaged?: boolean) => ({
    id: damaged ? `${unit}:damaged` : unit,
    value: damaged ? `${unit}:damaged` : unit,
    label: damaged ? `${unit} (damaged)` : unit,
    meta: damaged === undefined ? { unit, player } : { unit, player, damaged },
  });
  return {
    id: "dev",
    player_id: "yin",
    name: "Devotion",
    inputs: [
      { key: "ship", kind: "choice", label: "Your cruiser or destroyer to destroy",
        options: [opt("cruiser", "yin")] },
      { key: "target", kind: "choice", label: "Opponent's ship you assign the hit to",
        options: [opt("dreadnought", "sol", false), opt("dreadnought", "sol", true)] },
    ],
  } as unknown as OfferView;
}

const ship = (baseType: string, damaged: boolean): ShipEntity =>
  ({ id: `${baseType}-${damaged ? 0 : 1}`, baseType, damaged }) as unknown as ShipEntity;

describe("shipPickSteps — Devotion (F_yin: Yin wskazuje konkretny statek)", () => {
  it("najpierw własny krążownik Yin, potem okręt przeciwnika", () => {
    const first = shipPickSteps([devotion()], ["yin", "sol"]);
    expect([...first.keys()]).toEqual(["yin"]);
    expect(first.get("yin")?.input.key).toBe("ship");

    const second = shipPickSteps([devotion()], ["yin", "sol"], { dev: { ship: "cruiser" } });
    expect([...second.keys()]).toEqual(["sol"]);
    const step = second.get("sol")!;
    expect(step.offer.player_id).toBe("yin"); // decyduje Yin, klika okręty rywala
    expect(step.chosen).toEqual({ ship: "cruiser" });
  });

  it("uszkodzony i nieuszkodzony pancernik to różne cele", () => {
    const step = shipPickSteps([devotion()], ["yin", "sol"], { dev: { ship: "cruiser" } })
      .get("sol")!;
    const pick = (damaged: boolean) =>
      step.input.options.find((o) => optionMatchesShip(o, ship("dreadnought", damaged)))?.id;
    expect(pick(true)).toBe("dreadnought:damaged");
    expect(pick(false)).toBe("dreadnought");
  });
});

describe("assignableShips — wymuszony cel trafień", () => {
  const ships = [ship("dreadnought", true), ship("dreadnought", false), ship("destroyer", false)];
  const target = (damaged: boolean | null, chooser = "yin") => ({
    types: ["dreadnought"], count: 1, label: "Devotion", damaged, chooser,
  });

  it("Devotion na uszkodzony: klikalny tylko uszkodzony pancernik", () => {
    expect(assignableShips(ships, target(true), 1).map((s) => s.id)).toEqual(["dreadnought-0"]);
  });

  it("Devotion na nieuszkodzony: tylko nieuszkodzony", () => {
    expect(assignableShips(ships, target(false), 1).map((s) => s.id)).toEqual(["dreadnought-1"]);
  });

  it("naprawiony w międzyczasie cel = ten typ, nieuszkodzony (jak silnik)", () => {
    const healed = [ship("dreadnought", false), ship("destroyer", false)];
    expect(assignableShips(healed, target(true), 1).map((s) => s.id)).toEqual(["dreadnought-1"]);
  });

  it("cel tylko na część trafień albo brak celu: wszystkie okręty", () => {
    expect(assignableShips(ships, target(true), 2)).toHaveLength(3);
    expect(assignableShips(ships, null, 1)).toHaveLength(3);
  });
});
