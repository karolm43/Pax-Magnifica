import { describe, expect, it } from "vitest";
import { groupSampleFiles, pickVariant, soundOfFile } from "./battleSound";
import { allowSound, groundKindOf, GROUND_DEATH_TIMING } from "./GroundDeathFx";
import { groundWeapon } from "./BattleOverlay";

describe("próbki dźwięku walki", () => {
  it("nazwa zdarzenia z pliku wariantu", () => {
    expect(soundOfFile("battle/rifle-2.ogg")).toBe("rifle");
    expect(soundOfFile("battle/explosionHeavy-1.ogg")).toBe("explosionHeavy");
    expect(soundOfFile("laser.mp3")).toBe("laser");
  });

  it("grupuje warianty jednego zdarzenia; stary format = same nazwy mp3", () => {
    const grouped = groupSampleFiles({
      files: ["battle/rifle-1.ogg", "battle/rifle-2.ogg", "battle/podLand-1.ogg"],
    });
    expect(grouped.get("rifle")).toEqual(["battle/rifle-1.ogg", "battle/rifle-2.ogg"]);
    expect(grouped.get("podLand")).toEqual(["battle/podLand-1.ogg"]);
    expect(groupSampleFiles({ sounds: ["laser"] }).get("laser")).toEqual(["laser.mp3"]);
  });

  it("losuje wariant inny niż poprzednio zagrany", () => {
    const seq = [0, 0, 0.99, 0.99, 0.5];
    let i = 0;
    const rnd = () => seq[i++ % seq.length];
    let last = -1;
    for (let k = 0; k < 5; k++) {
      const n = pickVariant("test-shot", 3, rnd);
      expect(n).toBeGreaterThanOrEqual(0);
      expect(n).toBeLessThan(3);
      expect(n).not.toBe(last);
      last = n;
    }
    expect(pickVariant("test-single", 1)).toBe(0);
  });
});

describe("walka naziemna", () => {
  it("piechota strzela z karabinu, mech (i reszta) z działa", () => {
    expect(groundWeapon("gf")).toBe("tracer");
    expect(groundWeapon("mf")).toBe("shell");
    expect(groundWeapon("pd")).toBe("shell");
  });

  it("piechota i mech giną inaczej; okręty nie są jednostkami naziemnymi", () => {
    expect(groundKindOf("gf")).toBe("infantry");
    expect(groundKindOf("mf")).toBe("mech");
    expect(groundKindOf("dd")).toBeNull();
  });

  it("sekwencje śmierci mieszczą się w czasie konania jednostki (3,8 s)", () => {
    const all = [
      ...Object.values(GROUND_DEATH_TIMING.infantry),
      ...Object.values(GROUND_DEATH_TIMING.mech),
    ];
    for (const ms of all) expect(ms).toBeLessThan(3800);
    expect(GROUND_DEATH_TIMING.mech.blast).toBeGreaterThan(GROUND_DEATH_TIMING.mech.powerDown);
  });

  it("ginący oddział nie robi chóru: limit krzyków w oknie czasu", () => {
    expect(allowSound("t-cry", 2, 700, 1000)).toBe(true);
    expect(allowSound("t-cry", 2, 700, 1100)).toBe(true);
    expect(allowSound("t-cry", 2, 700, 1200)).toBe(false);
    expect(allowSound("t-cry", 2, 700, 1800)).toBe(true);
  });
});
