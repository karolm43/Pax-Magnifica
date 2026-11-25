import type { NamedKind } from "@/domains/game-shell/components/ActivityPanel/Named";
import type { AgendaPhaseData, Objective, PlayerData } from "@/entities/data/types";
import type { EmpireStats } from "./empireStats";

/*
 * Wskazówki PANELU DOWÓDCY: czysta funkcja z danych web-data (nic nie liczy reguł - tylko czyta
 * stan, który policzył silnik: postęp celów, głosy, żetony, ręka). Każda wskazówka może wskazać
 * komponenty gry (``refs``) - UI pokazuje je jako nazwy z opisem po najechaniu.
 */

export type TipTone = "action" | "good" | "warn" | "info";

export type TipRef = { kind: NamedKind; id: string; name?: string };

export type Tip = { id: string; tone: TipTone; text: string; refs?: TipRef[] };

export type TipContext = {
  player: PlayerData;
  players: PlayerData[];
  objectives: Objective[];
  vpsToWin: number;
  /** Faza z gameState („action”, „strategy”, „status.*”, „agenda.*”). */
  phase: string;
  /** Czy to tura tego gracza (``activeTurnPlayer``). */
  isTurn: boolean;
  agenda: AgendaPhaseData | null;
  /** Statystyki imperium (``empireStats``); brak = bez porad o planszy. */
  empire?: EmpireStats;
  /**
   * Who is reading the briefing (the desk player). When it is someone else than ``player``,
   * the briefing switches to OPPONENT INTEL (what that player threatens), not "what to do".
   */
  viewer?: PlayerData | null;
};

/** ``self`` = my own seat (or no seat - spectator); ``scout`` = another player viewed from my seat. */
export function briefingMode(ctx: Pick<TipContext, "player" | "viewer">): "self" | "scout" {
  return ctx.viewer && ctx.viewer.discordId !== ctx.player.discordId ? "scout" : "self";
}

const ORDINAL = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th"];

function seated(players: PlayerData[]): PlayerData[] {
  return players.filter((p) => p.faction && p.faction !== "neutral" && !p.eliminated);
}

/** Miejsce w wyścigu o punkty (1 = prowadzi; remis = to samo miejsce). */
export function vpRank(player: PlayerData, players: PlayerData[]): number {
  return 1 + seated(players).filter((p) => p.totalVps > player.totalVps).length;
}

/** Cele publiczne, które gracz może zdobyć TERAZ (postęp ≥ próg, jeszcze niezdobyte). */
export function scorableObjectives(player: PlayerData, objectives: Objective[]): Objective[] {
  return objectives.filter(
    (o) =>
      o.revealed &&
      o.progressThreshold > 0 &&
      !o.scoredFactions.includes(player.faction) &&
      (o.factionProgress[player.faction] ?? 0) >= o.progressThreshold,
  );
}

/** Cele, do których brakuje JEDNEGO kroku (np. 2/3 planet). */
export function nearObjectives(player: PlayerData, objectives: Objective[]): Objective[] {
  return objectives.filter(
    (o) =>
      o.revealed &&
      o.progressThreshold > 1 &&
      !o.scoredFactions.includes(player.faction) &&
      (o.factionProgress[player.faction] ?? 0) === o.progressThreshold - 1,
  );
}

function phaseTips(ctx: TipContext): Tip[] {
  const { player, phase, isTurn, agenda } = ctx;
  const tips: Tip[] = [];
  const unplayed = player.scs.filter((sc) => !player.exhaustedSCs.includes(sc));
  if (phase === "strategy") {
    tips.push(
      player.scs.length === 0
        ? { id: "pick-sc", tone: "action", text: "Strategy phase: pick a strategy card when it is your turn." }
        : {
            id: "picked-sc",
            tone: "info",
            text: "Strategy card chosen - it sets your initiative in the action phase.",
            refs: player.scs.map((sc) => ({ kind: "strategy", id: String(sc) })),
          },
    );
  } else if (phase === "action") {
    if (player.passed) {
      tips.push({
        id: "passed",
        tone: "info",
        text: "You passed: no more turns this round, but you can still follow secondaries and react.",
      });
    } else if (isTurn) {
      const left = player.actionsLeft ?? (player.tookActionThisTurn ? 0 : 1);
      tips.push({
        id: "your-turn",
        tone: "action",
        text:
          left > 0
            ? `Your turn: take a tactical, strategic or component action (${left} left), then end your turn.`
            : "Action taken - end your turn (or pass if your strategy card is played).",
      });
    }
    if (!player.passed && unplayed.length > 0) {
      tips.push({
        id: "play-sc",
        tone: "warn",
        text: "You must play your strategy card before you can pass.",
        refs: unplayed.map((sc) => ({ kind: "strategy", id: String(sc) })),
      });
    }
  } else if (phase.startsWith("status")) {
    // ``numScoreableSecrets`` is the secret-objective LIMIT (web_objectives.py), not "scorable now".
    if (player.numUnscoredSecrets > 0) {
      tips.push({
        id: "secret",
        tone: "good",
        text: `Status phase: you hold ${player.numUnscoredSecrets} unscored secret objective(s) - score one whose condition you meet.`,
      });
    }
    tips.push({
      id: "status",
      tone: "info",
      text: "Status phase: score up to 1 public and 1 secret objective, then redistribute command tokens.",
    });
  } else if (phase.startsWith("agenda") && agenda) {
    const voter = agenda.voters[player.discordId];
    const votes = voter ? voter.available + voter.extra : 0;
    const place = agenda.voteOrder.indexOf(player.discordId);
    if (agenda.blocked.includes(player.discordId)) {
      tips.push({ id: "blocked", tone: "warn", text: "You cannot vote on this agenda." });
    } else if (agenda.currentVoter === player.discordId) {
      tips.push({ id: "vote-now", tone: "action", text: `Your vote: ${votes} votes from ready planets.` });
    } else if (player.discordId in agenda.votes || agenda.abstained.includes(player.discordId)) {
      tips.push({ id: "voted", tone: "info", text: "You have already voted on this agenda." });
    } else if (place >= 0) {
      tips.push({
        id: "vote-order",
        tone: "info",
        text: `You vote ${ORDINAL[place] ?? `#${place + 1}`} of ${agenda.voteOrder.length} - ${votes} votes ready.`,
      });
    }
    if (agenda.card) {
      tips.push({
        id: "agenda-card",
        tone: "info",
        text: "On the floor:",
        refs: [{ kind: "agenda", id: agenda.card.id, name: agenda.card.name }],
      });
    }
  }
  return tips;
}

function objectiveTips(ctx: TipContext): Tip[] {
  const { player, objectives } = ctx;
  const tips: Tip[] = [];
  const ready = scorableObjectives(player, objectives);
  if (ready.length > 0) {
    tips.push({
      id: "score-ready",
      tone: "good",
      text: `Ready to score in the status phase (${ready.reduce((s, o) => s + o.pointValue, 0)} VP):`,
      refs: ready.map((o) => ({ kind: "objective", id: o.key, name: o.name })),
    });
  }
  const near = nearObjectives(player, objectives);
  if (near.length > 0) {
    tips.push({
      id: "score-near",
      tone: "info",
      text: "One step away from:",
      refs: near.map((o) => ({ kind: "objective", id: o.key, name: withProgress(o, player) })),
    });
  }
  return tips;
}

/** Objective name with the engine's progress for that player, e.g. "Expand Borders (5/6)". */
function withProgress(o: Objective, player: PlayerData): string {
  return `${o.name} (${o.factionProgress[player.faction] ?? 0}/${o.progressThreshold})`;
}

function displayName(p: PlayerData): string {
  return p.flexibleDisplayName || p.faction;
}

/** Strategy cards played by others that this player has not followed yet (web-data ``unfollowedSCs``). */
function secondaryTips(ctx: TipContext): Tip[] {
  const pending = ctx.player.unfollowedSCs ?? [];
  if (pending.length === 0) return [];
  return [
    {
      id: "follow-secondary",
      tone: "action",
      text: "Secondary abilities you can still follow:",
      refs: pending.map((sc) => ({ kind: "strategy", id: String(sc) })),
    },
  ];
}

function raceTips(ctx: TipContext): Tip[] {
  const { player, players, vpsToWin } = ctx;
  const others = seated(players).filter((p) => p.discordId !== player.discordId);
  const leader = [...others].sort((a, b) => b.totalVps - a.totalVps)[0];
  const need = Math.max(0, vpsToWin - player.totalVps);
  const rank = vpRank(player, players);
  let text = `${ORDINAL[rank - 1] ?? `#${rank}`} place - ${need} VP to victory (${player.totalVps}/${vpsToWin}).`;
  if (leader && leader.totalVps > player.totalVps) {
    text += ` Leader: ${leader.flexibleDisplayName || leader.faction} with ${leader.totalVps}.`;
  } else if (leader && leader.totalVps >= vpsToWin - 2) {
    text += ` Watch out: ${leader.flexibleDisplayName || leader.faction} is close to winning.`;
  }
  return [{ id: "race", tone: "info", text }];
}

function economyTips(ctx: TipContext): Tip[] {
  const { player } = ctx;
  const tips: Tip[] = [];
  // Limit liczy silnik (Executive Sanctions zmienia go na 3); brak = bez limitu.
  const limit = player.actionCardLimit;
  if (typeof limit === "number" && player.acCount > limit) {
    tips.push({
      id: "hand-limit",
      tone: "warn",
      text: `${player.acCount} action cards - over your limit of ${limit}, discard the excess.`,
    });
  }
  if (player.commoditiesTotal > 0 && player.commodities >= player.commoditiesTotal) {
    tips.push({
      id: "comms-full",
      tone: "info",
      text: `Commodities full (${player.commodities}/${player.commoditiesTotal}): trade them to a neighbour - for them they become trade goods.`,
    });
  }
  if (player.tacticalCC === 0) {
    tips.push({
      id: "no-tactic",
      tone: "warn",
      text: "No tactic tokens: you cannot activate systems. Component actions and passing still work.",
    });
  }
  if (player.ccReinf === 0) {
    tips.push({
      id: "no-reinf",
      tone: "warn",
      text: "No command tokens left in reinforcements - you cannot gain more.",
    });
  }
  const exhausted = player.exhaustedPlanets.filter((p) => player.planets.includes(p)).length;
  if (player.planets.length > 0 && exhausted === player.planets.length) {
    tips.push({
      id: "all-exhausted",
      tone: "info",
      text: "All your planets are exhausted - they ready in the status phase.",
    });
  }
  return tips;
}

function componentTips(ctx: TipContext): Tip[] {
  const { player } = ctx;
  const tips: Tip[] = [];
  const ready = player.leaders.filter(
    (l) => !l.locked && !l.exhausted && !l.purged && l.type !== "commander",
  );
  if (ready.length > 0) {
    tips.push({
      id: "leaders",
      tone: "good",
      text: "Ready leaders:",
      refs: ready.map((l) => ({ kind: "leader", id: l.id })),
    });
  }
  // Commanders have no exhaust: once unlocked their ability is always on - a reminder to use it.
  const commanders = player.leaders.filter((l) => l.type === "commander" && !l.locked && !l.purged);
  if (commanders.length > 0) {
    tips.push({
      id: "commanders",
      tone: "info",
      text: "Commander unlocked - its ability is active:",
      refs: commanders.map((l) => ({ kind: "leader", id: l.id })),
    });
  }
  if ((player.lawsOwned ?? []).length > 0) {
    tips.push({
      id: "laws",
      tone: "info",
      text: "Laws you hold:",
      refs: (player.lawsOwned ?? []).map((id) => ({ kind: "agenda", id })),
    });
  }
  return tips;
}

/** Porady z planszy: specjalizacje, PRODUCTION, pula floty, posiłki (R_planets, R_fleet_pool). */
function empireTips(ctx: TipContext): Tip[] {
  const { empire } = ctx;
  if (!empire) return [];
  const tips: Tip[] = [];
  const skips = Object.entries(empire.skips).filter(([, n]) => n > 0);
  if (skips.length > 0) {
    tips.push({
      id: "skips",
      tone: "info",
      text: `Ready tech specialties: ${skips.map(([c, n]) => `${n} ${c}`).join(", ")} - exhaust such a planet to satisfy a prerequisite when researching.`,
    });
  }
  if (empire.systems.present > 0 && empire.maxProduction === 0) {
    tips.push({
      id: "no-production",
      tone: "warn",
      text: "None of your units on the board has PRODUCTION - you cannot produce units in a tactical action.",
    });
  }
  if (empire.fleetPool > 0 && empire.largestFleet >= empire.fleetPool) {
    tips.push({
      id: "fleet-pool",
      tone: "warn",
      text: `Your largest fleet has ${empire.largestFleet} non-fighter ships - at your fleet pool limit (${empire.fleetPool}). Add fleet tokens before growing it.`,
    });
  }
  if (empire.depleted.length > 0) {
    tips.push({
      id: "depleted",
      tone: "info",
      text: `Nothing left in reinforcements: ${empire.depleted.join(", ")} - you cannot produce more of these.`,
    });
  }
  return tips;
}

/**
 * OPPONENT INTEL: the same web-data read from the other side of the table - what this player
 * can score, how close they are to winning, what they still hold. Tones are from the viewer's
 * point of view: ``warn`` = a threat to me, ``good`` = an opening for me.
 */
function intelTips(ctx: TipContext): Tip[] {
  const { player, objectives, vpsToWin, viewer, empire } = ctx;
  const name = displayName(player);
  const tips: Tip[] = [];
  const need = Math.max(0, vpsToWin - player.totalVps);
  const rank = vpRank(player, ctx.players);
  tips.push({
    id: "intel-race",
    tone: need <= 2 ? "warn" : "info",
    text: `${name}: ${ORDINAL[rank - 1] ?? `#${rank}`} place, ${need} VP from victory (${player.totalVps}/${vpsToWin}).`,
  });
  const ready = scorableObjectives(player, objectives);
  if (ready.length > 0) {
    tips.push({
      id: "intel-score-ready",
      tone: "warn",
      text: `Can score in the status phase (${ready.reduce((s, o) => s + o.pointValue, 0)} VP):`,
      refs: ready.map((o) => ({ kind: "objective", id: o.key, name: o.name })),
    });
  }
  const near = nearObjectives(player, objectives);
  if (near.length > 0) {
    tips.push({
      id: "intel-score-near",
      tone: "info",
      text: "One step away from:",
      refs: near.map((o) => ({ kind: "objective", id: o.key, name: withProgress(o, player) })),
    });
  }
  const unplayed = player.scs.filter((sc) => !player.exhaustedSCs.includes(sc));
  if (unplayed.length > 0) {
    tips.push({
      id: "intel-sc",
      tone: "info",
      text: player.passed ? "Strategy card held:" : "Strategy card still to play:",
      refs: unplayed.map((sc) => ({ kind: "strategy", id: String(sc) })),
    });
  }
  if (viewer && (player.neighbors ?? []).includes(viewer.color)) {
    tips.push({
      id: "intel-neighbor",
      tone: "good",
      text: `${name} is your neighbour - you can trade with them (${player.commodities}/${player.commoditiesTotal} commodities, ${player.tg} trade goods).`,
    });
  }
  tips.push({
    id: "intel-hand",
    tone: "info",
    text: `In hand: ${player.acCount} action card(s), ${player.soCount ?? 0} unscored secret objective(s), ${player.pnCount ?? 0} promissory note(s).`,
  });
  if (empire && empire.fleetPool > 0) {
    tips.push({
      id: "intel-fleet",
      tone: empire.largestFleet >= empire.fleetPool ? "good" : "info",
      text:
        empire.largestFleet >= empire.fleetPool
          ? `Fleet pool ${empire.fleetPool} - their largest fleet (${empire.largestFleet}) is at the cap.`
          : `Fleet pool ${empire.fleetPool} - largest fleet ${empire.largestFleet} non-fighter ships.`,
    });
  }
  if (player.tacticalCC === 0 && ctx.phase === "action" && !player.passed) {
    tips.push({ id: "intel-no-tactic", tone: "good", text: "No tactic tokens left - they cannot activate systems." });
  }
  return tips;
}

/** Wszystkie wskazówki w kolejności ważności: co teraz → szanse na punkty → ostrzeżenia → reszta. */
export function commanderTips(ctx: TipContext): Tip[] {
  const order: Record<TipTone, number> = { action: 0, good: 1, warn: 2, info: 3 };
  const tips =
    briefingMode(ctx) === "scout"
      ? [...intelTips(ctx), ...componentTips(ctx).filter((t) => t.id !== "commanders")]
      : [
          ...phaseTips(ctx),
          ...secondaryTips(ctx),
          ...objectiveTips(ctx),
          ...economyTips(ctx),
          ...componentTips(ctx),
          ...empireTips(ctx),
          ...raceTips(ctx),
        ];
  return tips
    .map((tip, index) => ({ tip, index }))
    .sort((a, b) => order[a.tip.tone] - order[b.tip.tone] || a.index - b.index)
    .map(({ tip }) => tip);
}
