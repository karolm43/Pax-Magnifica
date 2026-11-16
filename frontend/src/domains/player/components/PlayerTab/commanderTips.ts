import type { NamedKind } from "@/domains/game-shell/components/ActivityPanel/Named";
import type { AgendaPhaseData, Objective, PlayerData } from "@/entities/data/types";

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
};

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
function nearObjectives(player: PlayerData, objectives: Objective[]): Objective[] {
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
    if (player.numScoreableSecrets > 0) {
      tips.push({
        id: "secret",
        tone: "good",
        text: `Status phase: you can score ${player.numScoreableSecrets} secret objective(s) now.`,
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
      refs: near.map((o) => ({ kind: "objective", id: o.key, name: o.name })),
    });
  }
  return tips;
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

/** Wszystkie wskazówki w kolejności ważności: co teraz → szanse na punkty → ostrzeżenia → reszta. */
export function commanderTips(ctx: TipContext): Tip[] {
  const order: Record<TipTone, number> = { action: 0, good: 1, warn: 2, info: 3 };
  const tips = [
    ...phaseTips(ctx),
    ...objectiveTips(ctx),
    ...economyTips(ctx),
    ...componentTips(ctx),
    ...raceTips(ctx),
  ];
  return tips
    .map((tip, index) => ({ tip, index }))
    .sort((a, b) => order[a.tip.tone] - order[b.tip.tone] || a.index - b.index)
    .map(({ tip }) => tip);
}
