/*
 * Decyzje „wskaż okręt" w oknie bitwy: obie strony mogą decydować naraz (np. obie mają
 * Assault Cannon) — każda dostaje SWOJĄ ofertę, nie tylko pierwsza z listy.
 */
import { describe, expect, it } from "vitest";
import type { OfferView } from "@/api/useOffers";
import {
  canPick,
  complete,
  currentInput,
  optionMatchesShip,
  pickValues,
  shipPickOffers,
  shipPickSteps,
  togglePick,
} from "./shipPick";
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
  const cruiser = ship("cruiser", false);

  it("najpierw własny krążownik Yin, potem okręt przeciwnika; klik nic nie zatwierdza", () => {
    const offer = devotion();
    const first = shipPickSteps([offer], ["yin", "sol"]).get("yin")!;
    expect(first.input?.key).toBe("ship");
    // Na kroku 1 klikalny tylko własny krążownik, nie okręty Sol.
    expect(canPick(offer, {}, cruiser, "yin")).toBe(true);
    expect(canPick(offer, {}, ship("dreadnought", false), "sol")).toBe(false);

    const afterShip = togglePick(offer, {}, cruiser, "yin");
    expect(currentInput(offer, afterShip)?.key).toBe("target");
    expect(complete(offer, afterShip)).toBe(false);
    const done = togglePick(offer, afterShip, ship("dreadnought", true), "sol");
    expect(complete(offer, done)).toBe(true);
    expect(pickValues(offer, done)).toEqual({ ship: "cruiser", target: "dreadnought:damaged" });
  });

  it("ponowny klik odznacza - także wybór z wcześniejszego kroku", () => {
    const offer = devotion();
    const s1 = togglePick(offer, {}, cruiser, "yin");
    const s2 = togglePick(offer, s1, ship("dreadnought", false), "sol");
    const undone = togglePick(offer, s2, cruiser, "yin");
    expect(pickValues(offer, undone)).toEqual({ target: "dreadnought" });
    expect(currentInput(offer, undone)?.key).toBe("ship");
  });

  it("uszkodzony i nieuszkodzony pancernik to różne cele", () => {
    const input = devotion().inputs[1] as unknown as {
      options: Parameters<typeof optionMatchesShip>[0][];
    };
    const pick = (damaged: boolean) =>
      input.options.find((o) => optionMatchesShip(o, ship("dreadnought", damaged)))?.id;
    expect(pick(true)).toBe("dreadnought:damaged");
    expect(pick(false)).toBe("dreadnought");
  });
});

const unitOpt = (id: string, unit: string, player: string) => ({
  id, value: id, label: `${unit} - ${player}`, meta: { unit, player },
});

describe("decyzje z jednostkami obu stron i wyborem wielu", () => {
  it("Viscount Unlenn: statki OBU stron klikalne, decyzja pod oboma właścicielami", () => {
    const offer = {
      id: "vu", player_id: "letnev", name: "Viscount Unlenn",
      inputs: [{ key: "ship", kind: "choice", label: "Ship that rolls 1 additional die",
        options: [unitOpt("letnev|dreadnought", "dreadnought", "letnev"), unitOpt("sol|carrier", "carrier", "sol")] }],
    } as unknown as OfferView;
    const steps = shipPickSteps([offer], ["letnev", "sol"]);
    expect(steps.get("letnev")?.offer.id).toBe("vu");
    expect(steps.get("sol")?.offer.id).toBe("vu");
    const carrier = ship("carrier", false);
    // Typ musi się zgadzać z WŁAŚCICIELEM: lotniskowiec Sol, nie Letnev.
    expect(canPick(offer, {}, carrier, "letnev")).toBe(false);
    const picked = togglePick(offer, {}, carrier, "sol");
    expect(pickValues(offer, picked)).toEqual({ ship: "sol|carrier" });
    // Pojedynczy wybór: klik w inny statek zastępuje poprzedni.
    const swapped = togglePick(offer, picked, ship("dreadnought", false), "letnev");
    expect(pickValues(offer, swapped)).toEqual({ ship: "letnev|dreadnought" });
  });

  it("Ambush: do 2 okrętów, każdy klik to osobny egzemplarz", () => {
    const offer = {
      id: "amb", player_id: "mentak", name: "Ambush",
      inputs: [{ key: "ships", kind: "multi", label: "Ships that roll (up to 2)", min: 1, max: 2,
        options: ["cruiser:0", "cruiser:1", "destroyer:0"].map((id) =>
          unitOpt(id, id.split(":")[0], "mentak")) }],
    } as unknown as OfferView;
    const c1 = { ...ship("cruiser", false), id: "c1" } as ShipEntity;
    const c2 = { ...ship("cruiser", false), id: "c2" } as ShipEntity;
    const d1 = { ...ship("destroyer", false), id: "d1" } as ShipEntity;
    let state = togglePick(offer, {}, c1, "mentak");
    expect(complete(offer, state)).toBe(true); // min 1 - można już zatwierdzić
    state = togglePick(offer, state, c2, "mentak");
    expect(pickValues(offer, state)).toEqual({ ships: ["cruiser:0", "cruiser:1"] });
    // Limit 2: trzeci nie wchodzi, dopóki jeden nie zostanie odznaczony.
    expect(canPick(offer, state, d1, "mentak")).toBe(false);
    state = togglePick(offer, state, c1, "mentak");
    state = togglePick(offer, state, d1, "mentak");
    expect(pickValues(offer, state)).toEqual({ ships: ["cruiser:1", "destroyer:0"] });
  });

  it("decyzja z opcją bez jednostki (np. odmowa) zostaje w oknie decyzji", () => {
    const offer = {
      id: "x", player_id: "p1", name: "X",
      inputs: [{ key: "u", kind: "choice", label: "Unit",
        options: [unitOpt("a", "cruiser", "p1"), { id: "none", value: "none", label: "None" }] }],
    } as unknown as OfferView;
    expect(shipPickSteps([offer], ["p1", "p2"]).size).toBe(0);
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
