import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearMapMarks, mapRefKeys, showOnMap } from "./mapPeek";

describe("mapRefKeys", () => {
  it("planeta/system z meta i z wartości opcji", () => {
    expect(mapRefKeys("jord")).toEqual(["planet:jord", "system:jord"]);
    expect(mapRefKeys(3, { planet: "mr", position: "000" })).toEqual(["planet:mr", "system:000"]);
    expect(mapRefKeys(2)).toEqual([]);
  });

  it("wartości złożone silnika (pozycja|planeta, planeta>cel) wskazują każdą część", () => {
    expect(mapRefKeys("102|industrex")).toEqual(
      expect.arrayContaining(["system:102", "planet:industrex"]),
    );
    expect(mapRefKeys("mr>jord")).toEqual(expect.arrayContaining(["planet:mr", "planet:jord"]));
  });
});

describe("showOnMap / clearMapMarks", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <div data-search-key="planet:jord" data-search-scope="map" id="map-jord"></div>
      <div data-search-key="planet:jord" id="card-jord"></div>
      <div data-search-key="system:101" data-search-scope="map-tile" id="tile"></div>`;
    // jsdom nie liczy układu - każdy element udaje, że ma pudełko.
    vi.spyOn(Element.prototype, "getClientRects").mockReturnValue([{}] as unknown as DOMRectList);
  });
  afterEach(() => {
    clearMapMarks();
    vi.restoreAllMocks();
  });

  it("podświetla tylko cel na MAPIE i zdejmuje znaczniki", () => {
    expect(showOnMap(["planet:jord"], { peek: true })).toBe(true);
    expect(document.getElementById("map-jord")?.hasAttribute("data-search-current")).toBe(true);
    expect(document.getElementById("card-jord")?.hasAttribute("data-search-match")).toBe(false);
    expect(document.body.hasAttribute("data-map-peek")).toBe(true);

    clearMapMarks();
    expect(document.getElementById("map-jord")?.hasAttribute("data-search-match")).toBe(false);
    expect(document.body.hasAttribute("data-map-peek")).toBe(false);
  });

  it("brak celu na mapie - nic się nie dzieje", () => {
    expect(showOnMap(["planet:nowhere"], { peek: true })).toBe(false);
    expect(document.body.hasAttribute("data-map-peek")).toBe(false);
  });
});
