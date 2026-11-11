/*
 * Lobby na żywo (RULES.md 44.5a): kto może edytować który slot kreatora.
 */
import { describe, expect, it } from "vitest";
import { canEditSlot } from "./setupSync";

const base = { owners: [], ownerNames: [], links: [] };

describe("canEditSlot", () => {
  it("tryb lokalny i host: każdy slot", () => {
    expect(canEditSlot({ ...base, active: false, isGuest: false, mySlot: null }, 3)).toBe(true);
    expect(canEditSlot({ ...base, active: true, isGuest: false, mySlot: 0 }, 3)).toBe(true);
  });

  it("gość: tylko swój slot", () => {
    const guest = { ...base, active: true, isGuest: true, mySlot: 2 };
    expect(canEditSlot(guest, 2)).toBe(true);
    expect(canEditSlot(guest, 0)).toBe(false);
  });
});
