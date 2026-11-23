import { afterEach, describe, expect, it } from "vitest";
import { act, render, renderHook } from "@testing-library/react";
import {
  PHASE_WINDOW,
  PHASE_WINDOW_SELECTOR,
  boxesOverlap,
  decisionZoneOverlaps,
  useDomPresence,
} from "./useDecisionZone";

const box = (left: number, top: number, right: number, bottom: number) => ({ left, top, right, bottom });

/** jsdom nie liczy układu - prostokąt elementu podajemy ręcznie. */
function placeAt(el: HTMLElement, r: ReturnType<typeof box>) {
  el.getBoundingClientRect = () =>
    ({ ...r, x: r.left, y: r.top, width: r.right - r.left, height: r.bottom - r.top, toJSON: () => r }) as DOMRect;
}

afterEach(() => {
  document.body.innerHTML = "";
});

describe("boxesOverlap", () => {
  it("wspólna część = nachodzą", () => {
    expect(boxesOverlap(box(0, 0, 100, 100), box(50, 50, 150, 150))).toBe(true);
  });

  it("styk krawędzi to jeszcze nie zasłonięcie", () => {
    expect(boxesOverlap(box(0, 0, 100, 100), box(100, 0, 200, 100))).toBe(false);
  });
});

describe("decisionZoneOverlaps", () => {
  it("wykrywa okno decyzji pod prostokątem, pomija elementy wewnątrz `ignore`", () => {
    const zone = document.createElement("section");
    zone.setAttribute("data-decision-zone", "");
    placeAt(zone, box(100, 500, 600, 800));
    document.body.append(zone);
    expect(decisionZoneOverlaps(box(0, 700, 1000, 900))).toBe(true);
    expect(decisionZoneOverlaps(box(0, 0, 1000, 400))).toBe(false);
    expect(decisionZoneOverlaps(box(0, 700, 1000, 900), document.body)).toBe(false);
  });

  it("niewyrenderowane okno (zerowy rozmiar) się nie liczy", () => {
    const zone = document.createElement("div");
    zone.setAttribute("data-decision-zone", "");
    document.body.append(zone);
    expect(decisionZoneOverlaps(box(0, 0, 1000, 1000))).toBe(false);
  });
});

describe("useDomPresence", () => {
  it("śledzi otwarcie i zamknięcie okna fazy", async () => {
    const { result } = renderHook(() => useDomPresence(PHASE_WINDOW_SELECTOR));
    expect(result.current).toBe(false);
    let unmount = () => {};
    // MutationObserver zgłasza zmiany w mikrozadaniu - act czeka na obietnicę.
    await act(() => {
      unmount = render(<aside {...PHASE_WINDOW} aria-label="Status phase" />).unmount;
      return Promise.resolve();
    });
    expect(result.current).toBe(true);
    await act(() => {
      unmount();
      return Promise.resolve();
    });
    expect(result.current).toBe(false);
  });
});
