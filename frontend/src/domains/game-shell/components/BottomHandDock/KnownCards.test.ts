import { describe, expect, it } from "vitest";
import { knownAgendaPlaces } from "./KnownCards";

describe("knownAgendaPlaces", () => {
  it("numeruje znane karty od góry i od spodu (ostatnia = sam spód)", () => {
    expect(knownAgendaPlaces(["a", "b"], ["y", "z"], null)).toEqual([
      { id: "a", place: "Top 1" },
      { id: "b", place: "Top 2" },
      { id: "z", place: "Bottom" },
      { id: "y", place: "Bottom 2" },
    ]);
  });

  it("M'aban uzupełnia wiedzę tylko tam, gdzie jej brak", () => {
    const maban = { neighbors: {}, agendaTop: "t", agendaBottom: "z" };
    expect(knownAgendaPlaces([], [], maban)).toEqual([
      { id: "t", place: "Top 1" },
      { id: "z", place: "Bottom" },
    ]);
    expect(knownAgendaPlaces(["a", "b"], [], maban)[0]).toEqual({ id: "a", place: "Top 1" });
  });
});
