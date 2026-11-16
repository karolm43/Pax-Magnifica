import type { AgendaPhaseData, Objective, PlayerData } from "@/entities/data/types";
import { commanderTips, scorableObjectives, vpRank, type TipContext } from "./commanderTips";

function player(over: Partial<PlayerData>): PlayerData {
  return {
    discordId: "p1",
    faction: "hacan",
    color: "yellow",
    flexibleDisplayName: "Hacan",
    totalVps: 3,
    scs: [],
    exhaustedSCs: [],
    passed: false,
    eliminated: false,
    numScoreableSecrets: 0,
    acCount: 2,
    commodities: 0,
    commoditiesTotal: 6,
    tacticalCC: 3,
    ccReinf: 8,
    planets: ["a"],
    exhaustedPlanets: [],
    leaders: [],
    lawsOwned: [],
    ...over,
  } as unknown as PlayerData;
}

function objective(over: Partial<Objective>): Objective {
  return {
    key: "corner",
    name: "Corner the Market",
    pointValue: 1,
    revealed: true,
    scoredFactions: [],
    peekingFactions: [],
    multiScoring: false,
    hasRedTape: false,
    progressThreshold: 4,
    factionProgress: {},
    ...over,
  };
}

function ctx(over: Partial<TipContext>): TipContext {
  const me = over.player ?? player({});
  return {
    player: me,
    players: [me, player({ discordId: "p2", faction: "sol", color: "blue", totalVps: 7 })],
    objectives: [],
    vpsToWin: 10,
    phase: "action",
    isTurn: false,
    agenda: null,
    ...over,
  };
}

const ids = (c: TipContext) => commanderTips(c).map((t) => t.id);

describe("commanderTips", () => {
  it("panel działa bez aktywnego gracza: w agendzie mówi, ile głosów i którą kolejką", () => {
    const agenda = {
      voteOrder: ["p2", "p1"],
      currentVoter: "p2",
      votes: {},
      abstained: [],
      blocked: [],
      voters: { p1: { available: 5, extra: 1, total: 6, planets: [] } },
      card: { id: "mutiny", name: "Mutiny" },
    } as unknown as AgendaPhaseData;
    const tips = commanderTips(ctx({ phase: "agenda.voting", agenda }));
    expect(tips.find((t) => t.id === "vote-order")?.text).toMatch(/2nd of 2 - 6 votes/);
    expect(tips.find((t) => t.id === "agenda-card")?.refs?.[0]).toMatchObject({ kind: "agenda", id: "mutiny" });
  });

  it("w statusie podpowiada cele gotowe do zdobycia (postęp z silnika)", () => {
    const ready = objective({ factionProgress: { hacan: 4 } });
    const near = objective({ key: "expand", name: "Expand Borders", factionProgress: { hacan: 3 } });
    const done = objective({ key: "x", scoredFactions: ["hacan"], factionProgress: { hacan: 9 } });
    expect(scorableObjectives(player({}), [ready, near, done]).map((o) => o.key)).toEqual(["corner"]);
    const c = ctx({ phase: "status.scoring", objectives: [ready, near, done] });
    expect(ids(c)).toEqual(expect.arrayContaining(["score-ready", "score-near", "status"]));
    // Najpierw szanse na punkty, na końcu informacje.
    expect(ids(c)[0]).toBe("score-ready");
  });

  it("w swojej turze: akcja teraz i ostrzeżenie o niezagranej karcie strategii", () => {
    const me = player({ scs: [3], actionsLeft: 1 });
    const c = ctx({ player: me, players: [me], isTurn: true });
    expect(ids(c).slice(0, 2)).toEqual(["your-turn", "play-sc"]);
  });

  it("ostrzega o limicie kart akcji wg limitu z silnika i braku żetonów taktyki", () => {
    const me = player({ acCount: 4, actionCardLimit: 3, tacticalCC: 0 });
    expect(ids(ctx({ player: me }))).toEqual(expect.arrayContaining(["hand-limit", "no-tactic"]));
    const unlimited = player({ acCount: 12, actionCardLimit: null });
    expect(ids(ctx({ player: unlimited }))).not.toContain("hand-limit");
  });

  it("wyścig VP: miejsce i lider", () => {
    const c = ctx({});
    expect(vpRank(c.player, c.players)).toBe(2);
    expect(commanderTips(c).find((t) => t.id === "race")?.text).toMatch(/2nd place - 7 VP to victory.*Leader: .* with 7/);
  });
});
