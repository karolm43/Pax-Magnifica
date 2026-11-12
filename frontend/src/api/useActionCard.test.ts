/*
 * Testy składania parametrów formularza karty akcji (RULES.md 53): format zgodny z tym,
 * czego oczekuje silnik (wartość opcji, merge słownika, listy, liczby, zakresy).
 */
import { describe, it, expect } from "vitest";
import { buildActionCardParams, type ActionCardInput } from "@/api/useActionCard";

const planet: ActionCardInput = {
  key: "planet",
  kind: "choice",
  label: "Planet",
  hint: "",
  merge: false,
  options: [
    { id: "jord", value: "jord", label: "Jord" },
    { id: "mr", value: "mr", label: "Mecatol Rex" },
  ],
};

const target: ActionCardInput = {
  key: "target",
  kind: "choice",
  label: "Ship",
  hint: "",
  merge: true,
  options: [
    {
      id: "000:p2:cruiser",
      value: { position: "000", owner: "p2", base_type: "cruiser" },
      label: "Cruiser",
    },
  ],
};

const infantry: ActionCardInput = {
  key: "planets",
  kind: "multi",
  label: "Infantry",
  hint: "",
  min: 1,
  max: 2,
  options: [
    { id: "jord#0", value: "jord", label: "Jord 1" },
    { id: "jord#1", value: "jord", label: "Jord 2" },
  ],
};

const tradeGoods: ActionCardInput = {
  key: "trade_goods",
  kind: "number",
  label: "Trade goods",
  hint: "",
  min: 0,
  max: 3,
};

describe("buildActionCardParams", () => {
  it("wybór pojedynczy zwraca wartość opcji i wymaga wyboru", () => {
    expect(buildActionCardParams([planet], {})).toEqual({ params: {}, ready: false });
    expect(buildActionCardParams([planet], { planet: "mr" })).toEqual({
      params: { planet: "mr" },
      ready: true,
    });
  });

  it("merge wkleja słownik opcji do parametrów", () => {
    const result = buildActionCardParams([target], { target: "000:p2:cruiser" });
    expect(result.ready).toBe(true);
    expect(result.params).toEqual({ position: "000", owner: "p2", base_type: "cruiser" });
  });

  it("multi zachowuje powtarzające się wartości i pilnuje zakresu", () => {
    const both = buildActionCardParams([infantry], { planets: ["jord#0", "jord#1"] });
    expect(both).toEqual({ params: { planets: ["jord", "jord"] }, ready: true });
    expect(buildActionCardParams([infantry], { planets: [] }).ready).toBe(false);
    expect(
      buildActionCardParams([infantry], { planets: ["jord#0", "jord#1", "x"] }).ready,
    ).toBe(false);
  });

  it("liczba domyślnie równa minimum i musi mieścić się w zakresie", () => {
    expect(buildActionCardParams([tradeGoods], {})).toEqual({
      params: { trade_goods: 0 },
      ready: true,
    });
    expect(buildActionCardParams([tradeGoods], { trade_goods: 5 }).ready).toBe(false);
  });

  it("formularz bez wejść jest od razu gotowy", () => {
    expect(buildActionCardParams([], {})).toEqual({ params: {}, ready: true });
  });
});

describe("buildActionCardParams - płatność", () => {
  const inputs: ActionCardInput[] = [
    {
      key: "planets",
      kind: "multi",
      label: "Planets to exhaust",
      hint: "",
      min: 0,
      max: 1,
      options: [{ id: "mr", value: "mr", label: "Mecatol Rex (1)", meta: { planet: "mr", value: 1 } }],
      payment: { cost: 2, valueKind: "resources", tradeGoods: "trade_goods" },
    },
    { key: "trade_goods", kind: "number", label: "Trade goods", hint: "", min: 0, max: 2 },
  ];

  it("nie jest gotowa, dopóki planety + TG nie pokryją kosztu", () => {
    expect(buildActionCardParams(inputs, {}).ready).toBe(false);
    expect(buildActionCardParams(inputs, { planets: ["mr"] }).ready).toBe(false);
    expect(buildActionCardParams(inputs, { planets: ["mr"], trade_goods: 1 }).ready).toBe(true);
    expect(buildActionCardParams(inputs, { trade_goods: 2 })).toEqual({
      params: { planets: [], trade_goods: 2 },
      ready: true,
    });
  });
});
