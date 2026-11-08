import type { ComponentType, ReactNode } from "react";
import {
  IconArrowsLeftRight,
  IconArrowsShuffle,
  IconBolt,
  IconCards,
  IconCompass,
  IconCrown,
  IconFlag,
  IconFlame,
  IconHexagon,
  IconPlayerPause,
  IconPlayerTrackNext,
  IconPlayerPlay,
  IconRocket,
  IconSettings,
  IconSwords,
  IconTarget,
  IconTrophy,
  IconUser,
} from "@tabler/icons-react";
import type {
  Activity,
  ActivityFact,
  ActivityKind,
  ActivityPlayer,
} from "@/api/useBoardEditor";
import {
  prettifyId,
  resolveObjectiveName,
  resolvePlanetName,
  resolveTechName,
} from "../GameEventPanel/eventFormatting";
import { getLeaderById } from "@/entities/lookup/leaders";
import { getStrategyCardByInitiative } from "@/entities/lookup/strategyCards";

type Glyph = ComponentType<{ size?: number; stroke?: number }>;

export type ActivityContext = {
  players: Record<string, ActivityPlayer>;
  systemName: (position: string) => string;
  strategyCardIdMap?: Record<number, string>;
};

export type DescribedFact = {
  key: string;
  tone: "good" | "bad" | "info";
  text: ReactNode;
};

export type Described = {
  Icon: Glyph;
  /** Comma-separated rgb triplet (e.g. "239, 68, 68") used as `--ek`. */
  tone: string;
  headline: ReactNode;
  facts: DescribedFact[];
};

const KIND_STYLE: Record<ActivityKind, { Icon: Glyph; tone: string }> = {
  turn: { Icon: IconPlayerTrackNext, tone: "var(--gd-gray)" },
  strategy: { Icon: IconCards, tone: "var(--gd-purple)" },
  tactical: { Icon: IconRocket, tone: "var(--gd-blue)" },
  combat: { Icon: IconSwords, tone: "var(--gd-red)" },
  economy: { Icon: IconArrowsLeftRight, tone: "var(--gd-cyan)" },
  scoring: { Icon: IconTrophy, tone: "var(--gd-green)" },
  exploration: { Icon: IconCompass, tone: "var(--gd-teal)" },
  misc: { Icon: IconBolt, tone: "var(--gd-yellow)" },
  godmode: { Icon: IconSettings, tone: "var(--gd-orange)" },
};

/** Action-specific glyphs that read better than the category default. */
const ACTION_GLYPH: Record<string, Glyph> = {
  "turn.pass": IconPlayerPause,
  "game.start": IconFlag,
  "phase.start": IconPlayerPlay,
  "round.start": IconArrowsShuffle,
  "speaker.set": IconCrown,
  "tactical.activate": IconHexagon,
  "objective.score": IconTarget,
  "spacecannon.fire": IconFlame,
  "setup.faction": IconUser,
};

function playerName(ctx: ActivityContext, id: string | null): string {
  if (!id) return "Someone";
  const p = ctx.players[id];
  if (!p) return prettifyId(id);
  if (p.display_name.trim()) return p.display_name.trim();
  return p.faction ? prettifyId(p.faction) : prettifyId(id);
}

function strategyCardName(ctx: ActivityContext, initiative: string | null) {
  if (!initiative) return "a strategy card";
  const n = Number(initiative);
  const card = Number.isFinite(n)
    ? getStrategyCardByInitiative(n, ctx.strategyCardIdMap)
    : undefined;
  return card?.name ?? `Strategy ${initiative}`;
}

function phaseLabel(phase: string | null): string {
  if (!phase) return "";
  const words = phase.replace(/[._]+/g, " ").trim().toLowerCase();
  return words ? words[0].toUpperCase() + words.slice(1) : "";
}

function name(ctx: ActivityContext, id: string | null): ReactNode {
  return <b>{playerName(ctx, id)}</b>;
}

function headlineFor(a: Activity, ctx: ActivityContext): ReactNode {
  const actor = name(ctx, a.actor_id);
  const target = name(ctx, a.target_id);
  const sys = a.subject ? ctx.systemName(a.subject) : "a system";
  switch (a.action) {
    case "game.start":
      return "The game begins";
    case "turn.end":
      return (
        <>
          {actor} ended their turn
          {a.target_id && <> · {target} is up</>}
        </>
      );
    case "turn.pass":
      return (
        <>
          {actor} passed
          {a.target_id && a.target_id !== a.actor_id && <> · {target} is up</>}
        </>
      );
    case "turn.next":
      return (
        <>
          Turn passes to {target}
        </>
      );
    case "phase.start":
      return <>{phaseLabel(a.subject)} phase begins</>;
    case "round.start":
      return <>Round {a.subject} begins</>;
    case "speaker.set":
      return <>{target} became Speaker</>;
    case "setup.faction":
      return <>{prettifyId(a.subject ?? "")} joined the table</>;
    case "strategy.pick":
      return (
        <>
          {actor} chose <i>{strategyCardName(ctx, a.subject)}</i>
        </>
      );
    case "strategy.play":
      return (
        <>
          {actor} played <i>{strategyCardName(ctx, a.subject)}</i>
        </>
      );
    case "strategy.secondary":
      return a.detail === "exec" ? (
        <>{actor} used the secondary ability</>
      ) : (
        <>{actor} declined the secondary ability</>
      );
    case "tactical.activate":
      return (
        <>
          {actor} activated <i>{sys}</i>
        </>
      );
    case "tactical.move":
      return (
        <>
          {actor} moved ships out of <i>{sys}</i>
        </>
      );
    case "tactical.produce":
      return (
        <>
          {actor} produced units in <i>{sys}</i>
        </>
      );
    case "tactical.end":
      return <>{actor} finished the tactical action</>;
    case "tactical.capture":
      return (
        <>
          {actor} took control of{" "}
          <i>{a.detail ? resolvePlanetName(a.detail) : "a planet"}</i>
        </>
      );
    case "tactical.component":
      return (
        <>
          {actor} used a component
          {a.subject && a.subject !== "other" && (
            <>
              : <i>{prettifyId(a.subject)}</i>
            </>
          )}
        </>
      );
    case "tech.exhaust":
      return (
        <>
          {actor} exhausted <i>{resolveTechName(a.subject ?? "")}</i>
        </>
      );
    case "leader.state":
      return (
        <>
          {actor} {a.detail ?? "updated"}{" "}
          <i>{getLeaderById(a.subject ?? "")?.name ?? prettifyId(a.subject ?? "")}</i>
        </>
      );
    case "combat.start":
      return (
        <>
          {actor} attacks {a.target_id ? target : "an enemy"}
          {a.subject && a.subject !== "space" ? (
            <> on <i>{resolvePlanetName(a.subject)}</i></>
          ) : (
            <> in space</>
          )}
        </>
      );
    case "combat.end":
      return (
        <>
          Battle between {actor}
          {a.target_id && <> and {target}</>} ended
        </>
      );
    case "combat.retreat_announce":
      return <>{actor} announced a retreat</>;
    case "combat.retreat":
      return (
        <>
          {actor} retreated
          {a.subject && <> to <i>{ctx.systemName(a.subject)}</i></>}
        </>
      );
    case "invasion.begin":
      return (
        <>
          {actor} began an invasion of <i>{sys}</i>
        </>
      );
    case "invasion.commit":
      return <>{actor} landed ground forces</>;
    case "spacecannon.fire":
      return <>{actor} fired Space Cannon</>;
    case "transaction":
      return (
        <>
          {actor} made a deal with {target}
        </>
      );
    case "debt.give":
      return (
        <>
          {actor} gave debt tokens to {target}
        </>
      );
    case "debt.return":
      return (
        <>
          {actor} returned debt tokens to {target}
        </>
      );
    case "objective.score":
      return (
        <>
          {actor} scored{" "}
          <i>{resolveObjectiveName(a.subject ?? "")}</i>
        </>
      );
    case "scoring.finish":
      return <>Scoring finished</>;
    case "scoring.redistribute":
      return <>{actor} redistributed command tokens</>;
    case "explore.draw":
      return (
        <>
          {actor} explored <i>{resolvePlanetName(a.subject ?? "")}</i>
        </>
      );
    case "explore.resolve":
      return <>{actor} resolved an exploration card</>;
    case "godmode.edit":
      return <>Manual correction (God-Mode)</>;
    case "update":
      return a.actor_id ? <>Result of {actor}'s action</> : <>State updated</>;
    default:
      return prettifyId(a.action.replace(/[._]/g, " "));
  }
}

function describeFact(
  fact: ActivityFact,
  index: number,
  a: Activity,
  ctx: ActivityContext,
): DescribedFact | null {
  // Show whose fact it is only when it is not the actor's own.
  const who =
    fact.player_id === a.actor_id ? null : (
      <b>{playerName(ctx, fact.player_id)}</b>
    );
  const prefix = who ? <>{who}: </> : null;
  const key = `${fact.type}-${fact.player_id}-${fact.value ?? fact.delta}-${index}`;
  const delta = fact.delta ?? 0;
  switch (fact.type) {
    case "vp":
      return {
        key,
        tone: delta > 0 ? "good" : "bad",
        text: (
          <>
            {prefix}
            {delta > 0 ? "+" : ""}
            {delta} VP
          </>
        ),
      };
    case "tg":
      return {
        key,
        tone: delta > 0 ? "good" : "bad",
        text: (
          <>
            {prefix}
            {delta > 0 ? "+" : ""}
            {delta} trade goods
          </>
        ),
      };
    case "tech":
      return {
        key,
        tone: "info",
        text: (
          <>
            {prefix}researched {resolveTechName(fact.value ?? "")}
          </>
        ),
      };
    case "planet_gained":
      if (a.action === "tactical.capture" && fact.value === a.detail) return null;
      return {
        key,
        tone: "good",
        text: (
          <>
            {prefix}gained {resolvePlanetName(fact.value ?? "")}
          </>
        ),
      };
    case "planet_lost":
      return {
        key,
        tone: "bad",
        text: (
          <>
            {prefix}lost {resolvePlanetName(fact.value ?? "")}
          </>
        ),
      };
    default:
      return null;
  }
}

export function describeActivity(
  a: Activity,
  ctx: ActivityContext,
): Described {
  const style = KIND_STYLE[a.kind] ?? KIND_STYLE.misc;
  const facts: DescribedFact[] = [];
  a.facts.forEach((fact, index) => {
    const described = describeFact(fact, index, a, ctx);
    if (described) facts.push(described);
  });
  return {
    Icon: ACTION_GLYPH[a.action] ?? style.Icon,
    tone: style.tone,
    headline: headlineFor(a, ctx),
    facts,
  };
}
