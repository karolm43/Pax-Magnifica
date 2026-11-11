/*
 * Testy tożsamości aktora (RULES.md 44.1a): nagłówek tylko do backendu, `?seat=` pamiętane w karcie.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { ACTOR_HEADER, readActingSeat, readSeatToken, withActorHeader } from "./actorIdentity";

function headerOf(init: RequestInit | undefined): string | null {
  return new Headers(init?.headers).get(ACTOR_HEADER);
}

describe("actorIdentity", () => {
  beforeEach(() => sessionStorage.clear());

  it("bez miejsca nie dokłada nagłówka (tryb lokalny)", () => {
    const init = { method: "POST" };
    expect(withActorHeader("/bot/turn/pass", init, null)).toBe(init);
  });

  it("dokłada nagłówek do backendu i zachowuje istniejące nagłówki", () => {
    const init = withActorHeader(
      "/bot/turn/pass",
      { method: "POST", headers: { "Content-Type": "application/json" } },
      "p2",
    );
    expect(headerOf(init)).toBe("p2");
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
    expect(init?.method).toBe("POST");
  });

  it("nie dokłada nagłówka do zasobów spoza backendu (CDN)", () => {
    expect(headerOf(withActorHeader("https://cdn.example.com/a.png", undefined, "p2"))).toBeNull();
    expect(headerOf(withActorHeader("/static/a.png", undefined, "p2"))).toBeNull();
  });

  it("?seat= zapamiętuje miejsce, puste ?seat= je czyści", () => {
    expect(readActingSeat("?seat=p3")).toBe("p3");
    expect(readActingSeat("")).toBe("p3");
    expect(readActingSeat("?seat=")).toBeNull();
    expect(readActingSeat("")).toBeNull();
  });
});

describe("token miejsca (gra sieciowa, RULES.md 44.2)", () => {
  beforeEach(() => sessionStorage.clear());

  it("?token= trafia do nagłówka X-Seat-Token (bez X-Actor-Id)", () => {
    const init = withActorHeader("/bot/state", undefined, null, "tok123");
    expect(new Headers(init?.headers).get("X-Seat-Token")).toBe("tok123");
    expect(headerOf(init)).toBeNull();
  });

  it("token pamiętany w karcie, puste ?token= czyści", () => {
    expect(readSeatToken("?token=abc")).toBe("abc");
    expect(readSeatToken("")).toBe("abc");
    expect(readSeatToken("?token=")).toBeNull();
  });
});
