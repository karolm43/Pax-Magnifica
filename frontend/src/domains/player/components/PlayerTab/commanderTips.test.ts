import type { AgendaPhaseData, Objective, PlayerData } from "@/entities/data/types";
import {
  briefingMode,
  commanderTips,
  scorableObjectives,
  vpRank,
  type TipContext,
} from "./commanderTips";

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
    numScoreableSecrets: 3,
    numUnscoredSecrets: 0,
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

  it("sekrety w statusie: liczba niezdobytych w ręce, nie limit sekretów (numScoreableSecrets)", () => {
    const none = ctx({ phase: "status.scoring" });
    expect(ids(none)).not.toContain("secret");
    const me = player({ numUnscoredSecrets: 2 } as Partial<PlayerData>);
    const tip = commanderTips(ctx({ player: me, phase: "status.scoring" })).find((t) => t.id === "secret");
    expect(tip?.text).toMatch(/you hold 2 unscored secret objective/);
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

  it("cel o krok od zdobycia pokazuje postęp z silnika (np. 3/4)", () => {
    const near = objective({ key: "expand", name: "Expand Borders", factionProgress: { hacan: 3 } });
    const tip = commanderTips(ctx({ objectives: [near] })).find((t) => t.id === "score-near");
    expect(tip?.refs?.[0]).toMatchObject({ kind: "objective", id: "expand", name: "Expand Borders (3/4)" });
  });

  it("przypomina o odblokowanym commanderze i secondary do podjęcia", () => {
    const me = player({
      unfollowedSCs: [5],
      leaders: [
        { id: "hacancommander", type: "commander", locked: false, exhausted: false, purged: false },
        { id: "hacanhero", type: "hero", locked: true, exhausted: false, purged: false },
      ],
    } as unknown as Partial<PlayerData>);
    const tips = commanderTips(ctx({ player: me }));
    expect(tips.find((t) => t.id === "commanders")?.refs).toEqual([{ kind: "leader", id: "hacancommander" }]);
    expect(tips.find((t) => t.id === "follow-secondary")).toMatchObject({
      tone: "action",
      refs: [{ kind: "strategy", id: "5" }],
    });
    expect(tips.find((t) => t.id === "leaders")).toBeUndefined();
  });

  it("tryb: własne miejsce / brak miejsca = odprawa, cudzy gracz = wywiad", () => {
    const me = player({});
    const other = player({ discordId: "p2", faction: "sol", color: "blue" });
    expect(briefingMode({ player: me, viewer: me })).toBe("self");
    expect(briefingMode({ player: me, viewer: null })).toBe("self");
    expect(briefingMode({ player: other, viewer: me })).toBe("scout");
  });

  it("wywiad: co rywal zdobędzie, ile mu brakuje, karty strategii, sąsiedztwo i ręka", () => {
    const me = player({});
    const rival = player({
      discordId: "p2",
      faction: "sol",
      color: "blue",
      flexibleDisplayName: "Sol",
      totalVps: 8,
      scs: [2, 7],
      exhaustedSCs: [2],
      neighbors: ["yellow"],
      soCount: 2,
      pnCount: 3,
      acCount: 5,
      tg: 4,
    } as Partial<PlayerData>);
    const ready = objective({ factionProgress: { sol: 4 } });
    const c = ctx({ player: rival, players: [me, rival], viewer: me, objectives: [ready], isTurn: true });
    const tips = commanderTips(c);
    const byId = Object.fromEntries(tips.map((t) => [t.id, t]));
    expect(byId["intel-race"]).toMatchObject({ tone: "warn" });
    expect(byId["intel-race"].text).toMatch(/Sol: 1st place, 2 VP from victory \(8\/10\)/);
    expect(byId["intel-score-ready"].refs?.[0]).toMatchObject({ id: "corner" });
    expect(byId["intel-sc"].refs).toEqual([{ kind: "strategy", id: "7" }]);
    expect(byId["intel-neighbor"].text).toMatch(/neighbour/);
    expect(byId["intel-hand"].text).toBe(
      "In hand: 5 action card(s), 2 unscored secret objective(s), 3 promissory note(s).",
    );
    // Wywiad nie mówi rywalowi „twoja tura” ani o jego limicie ręki.
    expect(tips.map((t) => t.id)).not.toEqual(expect.arrayContaining(["your-turn"]));
    expect(tips.some((t) => t.id === "race" || t.id === "play-sc")).toBe(false);
  });

  it("wyścig VP: miejsce i lider", () => {
    const c = ctx({});
    expect(vpRank(c.player, c.players)).toBe(2);
    expect(commanderTips(c).find((t) => t.id === "race")?.text).toMatch(/2nd place - 7 VP to victory.*Leader: .* with 7/);
  });
});
