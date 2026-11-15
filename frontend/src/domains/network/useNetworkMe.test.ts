import { describe, expect, it } from "vitest";
import { canActAs, type NetworkMe } from "./useNetworkMe";

const me = (over: Partial<NetworkMe>): NetworkMe => ({
  network: true,
  authenticated: true,
  player_id: null,
  host: false,
  ...over,
});

describe("canActAs", () => {
  it("tryb lokalny: każdy gracz", () => {
    expect(canActAs(me({ network: false }), "p2")).toBe(true);
  });
  it("host bez miejsca: każdy gracz", () => {
    expect(canActAs(me({ host: true }), "p2")).toBe(true);
  });
  it("gracz sieciowy (także host z miejscem): tylko siebie", () => {
    expect(canActAs(me({ player_id: "p1" }), "p1")).toBe(true);
    expect(canActAs(me({ player_id: "p1" }), "p2")).toBe(false);
    expect(canActAs(me({ player_id: "p1", host: true }), "p2")).toBe(false);
  });
  it("brak danych /network/me albo gracza: nie", () => {
    expect(canActAs(undefined, "p1")).toBe(false);
    expect(canActAs(me({ network: false }), null)).toBe(false);
  });
});
