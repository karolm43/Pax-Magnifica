/*
 * „Elect Planet” (U6): planeta wyniku agendy wybierana WYŁĄCZNIE na mapie.
 */
import { describe, expect, it } from "vitest";
import type { AgendaPhaseData } from "@/entities/data/types";
import { isPlanetAgenda, pickablePlanets, useAgendaMapPick } from "./AgendaMapPick";

describe("AgendaMapPick", () => {
  it("planety (nie typy planet) wybiera się na mapie", () => {
    expect(isPlanetAgenda("planet")).toBe(true);
    expect(isPlanetAgenda("planet_non_home")).toBe(true);
    expect(isPlanetAgenda("planet_trait")).toBe(false);
    expect(isPlanetAgenda("for_against")).toBe(false);
  });

  it("przy remisie świecą tylko remisowe planety", () => {
    const agenda = { step: "TIEBREAK", tied: ["mr"], outcomes: ["mr", "jord"] } as unknown as AgendaPhaseData;
    expect(pickablePlanets(agenda)).toEqual(["mr"]);
    expect(pickablePlanets({ ...agenda, step: "VOTE", tied: [] })).toEqual(["mr", "jord"]);
  });

  it("wskazana planeta czeka na odbiór przez okno Rady (jednorazowo)", () => {
    const store = useAgendaMapPick.getState();
    store.start();
    expect(useAgendaMapPick.getState().picking).toBe(true);
    useAgendaMapPick.getState().finish("jord");
    expect(useAgendaMapPick.getState().picking).toBe(false);
    expect(useAgendaMapPick.getState().take()).toBe("jord");
    expect(useAgendaMapPick.getState().take()).toBeNull();
  });
});
