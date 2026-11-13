import { describe, expect, it } from "vitest";
import type { Activity, ActivityEntry } from "@/api/useBoardEditor";
import { buildPlaylist } from "./music";
import { soundForClick } from "./uiSounds";
import { battleLines, cuesForEntry, type CueContext } from "./voiceCues";
import { buildVoiceBank, voiceCategory } from "./voices";

function entry(over: Partial<Activity>): ActivityEntry {
  return {
    seq: 1,
    is_current: true,
    created_at: null,
    activity: {
      kind: "tactical",
      action: "update",
      actor_id: null,
      target_id: null,
      subject: null,
      detail: null,
      round: 1,
      phase: "action",
      facts: [],
      ...over,
    },
  } as ActivityEntry;
}

const factions: Record<string, string> = { p1: "mentak", p2: "sol", p3: "winnu" };
const ctx = (over: Partial<CueContext> = {}): CueContext => ({
  me: "p2",
  network: true,
  isBot: () => false,
  factionOf: (pid) => factions[pid] ?? null,
  random: () => 0.99,
  ...over,
});

describe("voiceCategory", () => {
  it("normalizuje nazwy plików z assets/voices", () => {
    expect(voiceCategory("battle-3.mp3")).toBe("battle");
    expect(voiceCategory("home-defense-2.mp3")).toBe("homedefense");
    expect(voiceCategory("defenseoutnumbered.wav")).toBe("defenseoutnumbered");
    expect(voiceCategory("OrbitalDrop4.mp3")).toBe("orbitaldrop");
    expect(voiceCategory("special11.mp3")).toBe("special");
    expect(voiceCategory("specialb.mp3")).toBe("special");
    expect(voiceCategory("specialforgery2.mp3")).toBe("specialforgery");
  });

  it("grupuje pliki frakcji po kategorii", () => {
    const bank = buildVoiceBank({ hacan: ["battle-1.mp3", "battle-2.mp3", "joke1.mp3"] });
    expect(bank.hacan.battle).toEqual(["battle-1.mp3", "battle-2.mp3"]);
    expect(bank.hacan.joke).toEqual(["joke1.mp3"]);
  });
});

describe("cuesForEntry", () => {
  it("start walki daje sygnał bitwy z atakującym, obrońcą i systemem", () => {
    const cues = cuesForEntry(
      entry({ kind: "combat", action: "combat.start", actor_id: "p1", target_id: "p2", subject: "space", detail: "203" }),
      ctx(),
    );
    expect(cues).toContainEqual({ kind: "battle", attacker: "p1", defender: "p2", position: "203" });
  });

  it("zdolność frakcji z własnym nagraniem (Pillage) daje jej kwestię", () => {
    const cues = cuesForEntry(
      entry({
        facts: [{ type: "ability_used", player_id: "p1", value: "abilities:pillage", detail: null, delta: null }],
      }),
      ctx(),
    );
    expect(cues).toContainEqual({ kind: "voice", player: "p1", category: "pillage", fallback: "special" });
  });

  it("Reclamation Winnu i Orbital Drop Sol rozpoznane po id komponentu", () => {
    const winnu = cuesForEntry(
      entry({ action: "component.use", actor_id: "p3", subject: "reclamation", detail: "ability" }),
      ctx(),
    );
    expect(winnu.some((c) => c.kind === "voice" && c.category === "reclamation")).toBe(true);
    const sol = cuesForEntry(
      entry({ action: "component.use", actor_id: "p2", subject: "orbital_drop", detail: "ability" }),
      ctx(),
    );
    expect(sol.some((c) => c.kind === "voice" && c.category === "orbitaldrop")).toBe(true);
  });

  it("bohater frakcji daje kwestię special", () => {
    const cues = cuesForEntry(
      entry({ action: "leader.state", actor_id: "p1", subject: "mentakhero", detail: "purged" }),
      ctx(),
    );
    expect(cues).toContainEqual({ kind: "voice", player: "p1", category: "special" });
  });

  it("żart przy pasie tylko czasem", () => {
    const pass = entry({ kind: "turn", action: "turn.pass", actor_id: "p1", target_id: "p3" });
    expect(cuesForEntry(pass, ctx({ random: () => 0.1 }))).toContainEqual({ kind: "voice", player: "p1", category: "joke" });
    expect(cuesForEntry(pass, ctx({ random: () => 0.9 })).some((c) => c.kind === "voice")).toBe(false);
  });

  it("moja tura -> dźwięk tury; cudza -> nic", () => {
    const mine = entry({ kind: "turn", action: "turn.next", actor_id: "p1", target_id: "p2" });
    expect(cuesForEntry(mine, ctx())).toContainEqual({ kind: "ui", name: "turn" });
    const other = entry({ kind: "turn", action: "turn.next", actor_id: "p2", target_id: "p1" });
    expect(cuesForEntry(other, ctx()).some((c) => c.kind === "ui")).toBe(false);
  });

  it("propozycja transakcji do mnie -> transmisja; faza agendy -> przejście + transmisja", () => {
    const offer = entry({ kind: "economy", action: "transaction.proposed", actor_id: "p1", target_id: "p2" });
    expect(cuesForEntry(offer, ctx())).toContainEqual({ kind: "transmission" });
    const agenda = entry({ kind: "turn", action: "phase.start", subject: "agenda.readyToFlip" });
    expect(cuesForEntry(agenda, ctx())).toEqual([{ kind: "ui", name: "transition" }, { kind: "transmission" }]);
  });

  it("God-Mode milczy", () => {
    expect(cuesForEntry(entry({ kind: "godmode", action: "combat.start", actor_id: "p1" }), ctx())).toEqual([]);
  });
});

describe("battleLines", () => {
  const side = (hp: number, expectedHits: number) => ({ hp, expectedHits, unitCount: hp });
  const never = () => 0.99;

  it("walka w domu obrońcy: inwazja i obrona domu", () => {
    expect(battleLines("a", "d", { defenderHome: true, random: never })).toEqual([
      { player: "a", category: "homeinvasion" },
      { player: "d", category: "homedefense" },
    ]);
  });

  it("przewaga atakującego: offense superior; miażdżąca: także outnumbered obrońcy", () => {
    expect(
      battleLines("a", "d", { defenderHome: false, attackerSide: side(8, 4), defenderSide: side(5, 2), random: never }),
    ).toEqual([{ player: "a", category: "offensesuperior" }]);
    expect(
      battleLines("a", "d", { defenderHome: false, attackerSide: side(12, 6), defenderSide: side(2, 1), random: never }),
    ).toEqual([
      { player: "a", category: "offensesuperior" },
      { player: "d", category: "defenseoutnumbered" },
    ]);
  });

  it("wyrównana walka: okrzyk atakującego", () => {
    expect(
      battleLines("a", "d", { defenderHome: false, attackerSide: side(5, 2), defenderSide: side(5, 2), random: never }),
    ).toEqual([{ player: "a", category: "battle" }]);
  });
});

describe("music", () => {
  it("jedna wspólna playlista: pliki luzem i z podfolderów", () => {
    expect(buildPlaylist({ "": ["a.mp3"], bitwa: ["b.mp3"] })).toEqual([
      "/static/music/a.mp3",
      "/static/music/bitwa/b.mp3",
    ]);
  });
});

describe("soundForClick", () => {
  it("przycisk = click, zakładka = select, przełącznik = toggle, data-sound nadpisuje", () => {
    document.body.innerHTML = `
      <button id="b"><span id="inner">x</span></button>
      <div role="tab" id="t">tab</div>
      <div role="switch" id="s"></div>
      <button id="dis" disabled>x</button>
      <div data-sound="none"><button id="quiet">x</button></div>
      <button id="drop" data-sound="drop">x</button>
      <p id="plain">text</p>`;
    const el = (id: string) => document.getElementById(id);
    expect(soundForClick(el("inner"))).toBe("click");
    expect(soundForClick(el("t"))).toBe("select");
    expect(soundForClick(el("s"))).toBe("toggle");
    expect(soundForClick(el("dis"))).toBeNull();
    expect(soundForClick(el("quiet"))).toBeNull();
    expect(soundForClick(el("drop"))).toBe("drop");
    expect(soundForClick(el("plain"))).toBeNull();
  });
});
