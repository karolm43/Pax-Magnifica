import { describe, expect, it } from "vitest";
import { classifyOptions, type OptionLookups } from "./optionKinds";

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
});
