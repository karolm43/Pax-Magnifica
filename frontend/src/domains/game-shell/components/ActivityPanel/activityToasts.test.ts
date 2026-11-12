import { describe, expect, it } from "vitest";
import type { Activity, ActivityEntry } from "@/api/useBoardEditor";
import { activitySubject } from "./activitySubject";
import { shouldToast } from "./ActivityToasts";

function activity(over: Partial<Activity>): Activity {
  return {
    kind: "tactical",
    action: "tech.exhaust",
    actor_id: "p2",
    target_id: null,
    subject: "gd",
    detail: null,
    round: 1,
    phase: "action",
    facts: [],
    ...over,
  };
}

function entry(over: Partial<Activity>): ActivityEntry {
  return { seq: 5, is_current: true, created_at: null, activity: activity(over) } as ActivityEntry;
}

const noBots = () => false;

describe("shouldToast", () => {
  it("pokazuje cudzą akcję w grze sieciowej, ale nie moją", () => {
    expect(shouldToast(entry({}), "p1", noBots, true)).toBe(true);
    expect(shouldToast(entry({ actor_id: "p1" }), "p1", noBots, true)).toBe(false);
  });

  it("pomija God-Mode, zdarzenia bez sprawcy i szum zmiany tury", () => {
    expect(shouldToast(entry({ kind: "godmode", action: "godmode.edit" }), "p1", noBots, true)).toBe(false);
    expect(shouldToast(entry({ actor_id: null }), "p1", noBots, true)).toBe(false);
    expect(shouldToast(entry({ kind: "turn", action: "turn.next" }), "p1", noBots, true)).toBe(false);
    expect(shouldToast(entry({ kind: "turn", action: "turn.pass" }), "p1", noBots, true)).toBe(true);
  });

  it("w trybie lokalnym pokazuje tylko akcje botów", () => {
    const bots = (id: string) => id === "bot1";
    expect(shouldToast(entry({ actor_id: "bot1" }), null, bots, false)).toBe(true);
    expect(shouldToast(entry({ actor_id: "p1" }), null, bots, false)).toBe(false);
  });
});

describe("activitySubject", () => {
  it("bierze technologię z wyczerpania techu", () => {
    expect(activitySubject(activity({}))).toEqual({ kind: "tech", id: "gd" });
  });

  it("bierze zagraną kartę akcji z faktów", () => {
    const a = activity({
      kind: "misc",
      action: "card.play",
      subject: null,
      facts: [{ type: "action_card", player_id: "p2", value: "sabotage" } as Activity["facts"][number]],
    });
    expect(activitySubject(a)).toEqual({ kind: "actionCard", id: "sabotage" });
  });

  it("zwraca null, gdy nie ma karty z tekstem", () => {
    expect(activitySubject(activity({ kind: "tactical", action: "tactical.move", subject: "301" }))).toBeNull();
  });
});
