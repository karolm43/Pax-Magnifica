import { describe, expect, it } from "vitest";
import { units } from "@/entities/data/units";
import { protoWarSunLevel } from "./protoWarSun";

const byId = (id: string) => units.find((u) => u.id === id);

describe("protoWarSunLevel — oprawa Prototype War Sun (Muaat)", () => {
  it("I i II z danych jednostek, zwykły war sun bez oprawy", () => {
    expect(protoWarSunLevel(byId("muaat_warsun"))).toBe(1);
    expect(protoWarSunLevel(byId("muaat_warsun2"))).toBe(2);
    expect(protoWarSunLevel(byId("warsun"))).toBeNull();
    expect(protoWarSunLevel(undefined)).toBeNull();
    // Ogólny war sun wariantu z „muaat_warsun” w id, bez frakcji — inne frakcje go dostają.
    expect(protoWarSunLevel(byId("baldrick_muaat_warsun"))).toBeNull();
    expect(protoWarSunLevel(byId("tf-pws"))).toBe(1);
  });
});
