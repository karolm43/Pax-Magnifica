import { describe, expect, it } from "vitest";
import {
  classifyOptions,
  isDeclineOption,
  splitDeclines,
  stackRange,
  stacksOf,
  withStackCount,
  type OptionLookups,
} from "./optionKinds";

const look: OptionLookups = {
  isTech: (id) => ["nm", "gd"].includes(id),
  isPlayer: (id) => ["p1", "p2"].includes(id),
  isPlanet: (id) => ["jord", "mr"].includes(id),
  isSystem: (pos) => ["101", "000"].includes(pos),
};

const opt = (value: unknown, meta?: Record<string, unknown>) => ({
  id: String(typeof value === "string" ? value : JSON.stringify(value)),
  value,
  label: String(value),
  meta,
});

describe("classifyOptions", () => {
  it("technologie, gracze, planety i systemy", () => {
    expect(classifyOptions([opt("nm"), opt("gd")], look)?.kind).toBe("technology");
    expect(classifyOptions([opt("p1"), opt("p2")], look)?.kind).toBe("player");
    expect(classifyOptions([opt("jord"), opt("mr")], look)?.kind).toBe("planet");
    expect(classifyOptions([opt("101"), opt("000")], look)?.kind).toBe("system");
  });

  it("wartości złożone i meta wskazują cel na mapie", () => {
    const planets = classifyOptions([opt("101|jord"), opt("000|mr")], look);
    expect(planets?.kind).toBe("planet");
    expect(planets?.targets.get("101|jord")).toBe("jord");
    const systems = classifyOptions([opt("a", { position: "101" }), opt("b", { position: "000" })], look);
    expect(systems?.targets.get("b")).toBe("000");
  });

  it("odnośnik do planety / technologii to nadal mapa / drzewo, nie lista (Yin hero)", () => {
    const ref = (kind: string, id: string) => ({ ref: { kind, id } });
    const yin = classifyOptions(
      [opt("none"), opt("101|jord", ref("planet", "jord")), opt("000|mr", ref("planet", "mr"))],
      look,
    );
    expect(yin?.kind).toBe("planet");
    expect(yin?.targets.get("000|mr")).toBe("mr");
    expect(yin?.targets.has("none")).toBe(false);
    const swap = classifyOptions([opt("keep", ref("tech", "nm")), opt("gd", ref("tech", "gd"))], look);
    expect(swap?.kind).toBe("technology");
    expect(swap?.targets.get("keep")).toBe("nm");
    // Odnośnik do innego komponentu (karta strategii) - zwykłe kafelki z opisem.
    expect(classifyOptions([opt("1", ref("strategy", "1")), opt("jord")], look)).toBeNull();
  });

  it("gracze z opcją bez celu (Carth: self + gracze) zostają graczami", () => {
    const carth = classifyOptions([opt("self"), opt("p1"), opt("p2")], look);
    expect(carth?.kind).toBe("player");
    expect(carth?.targets.has("self")).toBe(false);
    expect(carth?.targets.get("p2")).toBe("p2");
  });

  it("mieszane, powtórzone cele albo jednostki = zwykłe kafelki", () => {
    expect(classifyOptions([opt("nm"), opt("jord")], look)).toBeNull();
    // Ta sama planeta w dwóch opcjach - ale różne systemy: wybór systemu na mapie.
    expect(classifyOptions([opt("101|jord"), opt("000|jord")], look)?.kind).toBe("system");
    expect(classifyOptions([opt("jord|a"), opt("jord|b")], look)).toBeNull();
    expect(classifyOptions([opt("x", { unit: "cruiser" })], look)).toBeNull();
    expect(classifyOptions([], look)).toBeNull();
  });

  it("kilka opcji na planetę = wybór na mapie z grupami (Xxekir Grom, nie lista)", () => {
    const unit = (u: string, planet: string, n: number) =>
      ({ id: `${u}|${planet}|${n}`, value: `${u}|${planet}|${n}`, label: u, meta: { unit: u, player: "p1", planet } });
    const hero = classifyOptions(
      [unit("pds", "jord", 0), unit("mech", "jord", 0), unit("mech", "jord", 1), unit("mech", "mr", 0)],
      look,
    );
    expect(hero?.kind).toBe("planet");
    expect(hero?.grouped).toBe(true);
    expect(hero?.targets.get("mech|mr|0")).toBe("mr");
    // Jedno miejsce z wieloma opcjami to nie wybór miejsca - liczniki jednostek bez mapy.
    expect(classifyOptions([unit("pds", "jord", 0), unit("mech", "jord", 0)], look)).toBeNull();
  });

  it("opcja odmowy obok celów i cel w wartości-słowniku", () => {
    const stymie = classifyOptions([opt("skip"), opt("101"), opt("000")], look);
    expect(stymie?.kind).toBe("system");
    expect(stymie?.targets.has("skip")).toBe(false);
    const merc = classifyOptions(
      [opt({ position: "101", planet: "jord" }), opt({ position: "000", planet: "mr" })],
      look,
    );
    expect(merc?.kind).toBe("planet");
  });
});

describe("stacksOf / withStackCount", () => {
  const mech = (n: number, planet = "jord") => ({
    id: `m${planet}${n}`,
    value: `m${n}`,
    label: n ? `Mech #${n + 1}` : "Mech",
    meta: { unit: "mech", player: "p1", planet },
  });

  it("jednakowe jednostki w jednym miejscu to jeden stos", () => {
    const stacks = stacksOf([mech(0), mech(1), mech(0, "mr"), opt("skip")]);
    expect(stacks.map((s) => s.options.length)).toEqual([2, 1, 1]);
  });

  it("licznik stosu bierze opcje po kolei w limicie pola", () => {
    const stack = [mech(0), mech(1), mech(2)];
    expect(withStackCount(["x"], stack, 2, 4)).toEqual(["x", "mjord0", "mjord1"]);
    expect(withStackCount(["x", "y", "z"], stack, 3, 4)).toEqual(["x", "y", "z", "mjord0"]);
    expect(withStackCount(["mjord0", "mjord1"], stack, 0, 4)).toEqual([]);
    expect(stackRange(["x", "mjord0"], stack, 3)).toEqual({ value: 1, max: 2 });
  });
});

describe("isDeclineOption / splitDeclines (pkt 6 planu okien decyzji)", () => {
  it("rozpoznaje odmowy po id/value „none” i po etykiecie", () => {
    const opts = [
      { id: "none", value: "none", label: "Do not place" },
      { id: "x", value: "", label: "- none -" },
      { id: "d", value: "d", label: "Decline - that player gains 1 trade good" },
      { id: "p", value: "p", label: "Mecatol Rex" },
      { id: "q", value: "q", label: "Nonexistent planet" },
    ];
    expect(opts.map(isDeclineOption)).toEqual([true, true, true, false, false]);
    expect(splitDeclines(opts).regular.map((o) => o.id)).toEqual(["p", "q"]);
  });
});
