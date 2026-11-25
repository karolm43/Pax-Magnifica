import { describe, expect, it } from "vitest";
import { spaceCannonRole } from "./spaceCannonRole";

const base = {
  isOpen: true,
  queue: ["sol", "hacan", "xxcha"],
  responded: [] as string[],
  current: "sol" as string | null,
  pending: null as { target: string } | null,
};
const panel = (patch: Partial<typeof base>) =>
  ({ ...base, ...patch }) as Parameters<typeof spaceCannonRole>[0];

describe("spaceCannonRole", () => {
  it("queued seat waits until its turn, then fires", () => {
    expect(spaceCannonRole(panel({}), "hacan")).toBe("wait");
    expect(spaceCannonRole(panel({ current: "hacan" }), "hacan")).toBe("fire");
  });

  it("seat that already fired or passed is done", () => {
    expect(
      spaceCannonRole(panel({ responded: ["sol", "hacan"], current: "xxcha" }), "hacan"),
    ).toBe("done");
  });

  it("seat targeted by the active player's shot covers hits even without Space Cannon", () => {
    expect(spaceCannonRole(panel({ pending: { target: "mentak" } }), "mentak")).toBe("assign");
  });

  it("seat neither queued nor targeted gets no window", () => {
    expect(spaceCannonRole(panel({}), "mentak")).toBeNull();
    expect(spaceCannonRole(panel({ isOpen: false }), "hacan")).toBeNull();
  });
});
