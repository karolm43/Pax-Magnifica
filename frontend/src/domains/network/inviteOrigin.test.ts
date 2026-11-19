import { describe, expect, it } from "vitest";
import { inviteOrigins } from "./inviteOrigin";

const at = (url: string) => {
  const u = new URL(url);
  return { protocol: u.protocol, hostname: u.hostname, port: u.port, origin: u.origin };
};

describe("inviteOrigins", () => {
  it("replaces localhost with the host's network addresses, keeping the port", () => {
    expect(inviteOrigins(["10.147.19.174", "192.168.1.115"], at("http://localhost:8000/game"))).toEqual([
      "http://10.147.19.174:8000",
      "http://192.168.1.115:8000",
    ]);
    expect(inviteOrigins(["192.168.1.5"], at("http://127.0.0.1:5173/"))).toEqual([
      "http://192.168.1.5:5173",
    ]);
  });

  it("keeps a page that already runs on a network address", () => {
    expect(inviteOrigins(["192.168.1.5"], at("http://192.168.1.5:8000/"))).toEqual([
      "http://192.168.1.5:8000",
    ]);
  });

  it("falls back to the page origin when no address is known", () => {
    expect(inviteOrigins([], at("http://localhost:8000/"))).toEqual(["http://localhost:8000"]);
  });
});
