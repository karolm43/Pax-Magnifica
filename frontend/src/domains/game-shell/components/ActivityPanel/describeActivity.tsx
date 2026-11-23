import type { ComponentType, ReactNode } from "react";
import {
  IconArrowBackUp,
  IconArrowsLeftRight,
  IconArrowsShuffle,
  IconBolt,
  IconCards,
  IconCompass,
  IconCrown,
  IconFlag,
  IconFlame,
  IconGavel,
  IconHexagon,
  IconHourglass,
  IconPlayerPause,
  IconPlayerPlay,
  IconPlayerTrackNext,
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
import { getExploration } from "@/entities/lookup/explorations";
import {
  describeEffectScope,
  prettifyId,
  resolveAgendaName,
  resolveEffectName,
  resolveCardName,
  resolveObjectiveName,
  resolvePlanetName,
  resolveSystemName,
  resolveTechName,
  resolveUnitName,
} from "../GameEventPanel/eventFormatting";
import { getLeaderById } from "@/entities/lookup/leaders";
import { promissoryNotes } from "@/entities/data/promissoryNotes";
import { Named } from "./Named";
import { PlayerTag } from "@/shared/ui/PlayerTag";
import { getStrategyCardByInitiative } from "@/entities/lookup/strategyCards";

type Glyph = ComponentType<{ size?: number; stroke?: number }>;

export type ActivityContext = {
  players: Record<string, ActivityPlayer>;
  systemName: (position: string) => string;
  /** Planets of a system with resources/influence, for the hover hint. */
  systemHint: (position: string) => string;
  strategyCardIdMap?: Record<number, string>;
};

export type DescribedFact = {
  key: string;
  tone: "good" | "bad" | "info" | "card";
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
  "turn.undo": IconArrowBackUp,
  "game.start": IconFlag,
  "phase.start": IconPlayerPlay,
  "round.start": IconArrowsShuffle,
  "speaker.set": IconCrown,
  "reactions.wait": IconHourglass,
  "reactions.window": IconHourglass,
  "reactions.quick": IconHourglass,
  "tactical.activate": IconHexagon,
  "objective.score": IconTarget,
  "agenda.reveal": IconGavel,
  "agenda.vote": IconGavel,
  "spacecannon.fire": IconFlame,
  "spacecannon.losses": IconFlame,
  "invasion.bombard": IconFlame,
  "invasion.defense": IconFlame,
  "invasion.establish": IconFlag,
  "combat.end": IconFlag,
  "setup.faction": IconUser,
};

function playerName(ctx: ActivityContext, id: string | null): string {
  if (!id) return "Someone";
  const p = ctx.players[id];
  if (!p) return prettifyId(id);
  if (p.display_name.trim()) return p.display_name.trim();
  return p.faction ? prettifyId(p.faction) : prettifyId(id);
}

/** Nazwa wyniku agendy: gracz, For/Against albo planeta (reszta - ładny id). */
function agendaOutcomeName(ctx: ActivityContext, outcome: string | null): ReactNode {
  if (!outcome) return "an outcome";
  if (ctx.players[outcome]) return name(ctx, outcome);
  if (outcome === "for" || outcome === "against") return prettifyId(outcome);
  return resolvePlanetName(outcome);
}

function strategyCardName(ctx: ActivityContext, initiative: string | null) {
  if (!initiative) return "a strategy card";
  const n = Number(initiative);
  const card = Number.isFinite(n)
    ? getStrategyCardByInitiative(n, ctx.strategyCardIdMap)
    : undefined;
  return card?.name ?? `Strategy ${initiative}`;
}

function exploreCardName(id: string | null): string {
  if (!id) return "an exploration card";
  return getExploration(id)?.name ?? prettifyId(id);
}

function phaseLabel(phase: string | null): string {
  if (!phase) return "";
  const words = phase.replace(/[._]+/g, " ").trim().toLowerCase();
  return words ? words[0].toUpperCase() + words.slice(1) : "";
}

/** Gracz w opisie zdarzenia: logo frakcji w obwódce koloru + nazwa w jego kolorze (``PlayerTag``). */
function name(ctx: ActivityContext, id: string | null): ReactNode {
  const p = id ? ctx.players[id] : undefined;
  if (!id || !p) return <b>{playerName(ctx, id)}</b>;
  return (
    <PlayerTag
      playerId={id}
      size={14}
      known={{ name: playerName(ctx, id), faction: p.faction, color: p.color }}
    />
  );
}

/**
 * Nazwa bitwy do feedu: „Space battle of <system>" / „Ground battle for <planeta>".
 * ``subject`` = "space" albo id planety, ``detail`` = pozycja systemu (starsze wpisy: brak).
 */
function battleName(a: Activity, ctx: ActivityContext): ReactNode {
  const where = a.subject;
  if (where && where !== "space") {
    return (
      <>
        Ground battle for <Named kind="planet" id={where} name={resolvePlanetName(where)} />
      </>
    );
  }
  if (!a.detail) return <>Space battle</>;
  return (
    <>
      Space battle of{" "}
      <Named kind="system" id={a.detail} name={ctx.systemName(a.detail)} systemText={ctx.systemHint(a.detail)} />
    </>
  );
}

/** System z pola ``detail`` (wpisy inwazji / Space Cannon) jako nazwany węzeł. */
function detailSystem(a: Activity, ctx: ActivityContext): ReactNode {
  if (!a.detail) return <i>the active system</i>;
  return <Named kind="system" id={a.detail} name={ctx.systemName(a.detail)} systemText={ctx.systemHint(a.detail)} />;
}

function headlineFor(a: Activity, ctx: ActivityContext): ReactNode {
  const actor = name(ctx, a.actor_id);
  const target = name(ctx, a.target_id);
  const sys = a.subject ? ctx.systemName(a.subject) : "a system";
  const sysNode = a.subject ? (
    <Named kind="system" id={a.subject} name={sys} systemText={ctx.systemHint(a.subject)} />
  ) : (
    <i>{sys}</i>
  );
  switch (a.action) {
    case "game.start":
      return "The game begins";
    case "turn.undo":
      return <>{actor} undid their last step</>;
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
    case "reactions.wait":
      return <>Someone asked for more time to react</>;
    case "reactions.window":
      return <>Reaction windows now last {a.subject} s</>;
    case "reactions.quick":
      return a.subject === "on"
        ? <>Quick windows on: a reaction window ends once everyone has passed</>
        : <>Quick windows off: reaction windows last their full time</>;
    case "setup.faction":
      return <>{prettifyId(a.subject ?? "")} joined the table</>;
    case "strategy.pick":
      return (
        <>
          {actor} chose <Named kind="strategy" id={a.subject ?? ""} idMap={ctx.strategyCardIdMap} name={strategyCardName(ctx, a.subject)} />
        </>
      );
    case "strategy.play":
      return (
        <>
          {actor} played <Named kind="strategy" id={a.subject ?? ""} idMap={ctx.strategyCardIdMap} name={strategyCardName(ctx, a.subject)} />
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
          {actor} activated {sysNode}
        </>
      );
    case "tactical.move":
      return (
        <>
          {actor} moved ships out of {sysNode}
        </>
      );
    case "tactical.produce":
      return (
        <>
          {actor} produced units in {sysNode}
        </>
      );
    case "tactical.end":
      return <>{actor} finished the tactical action</>;
    case "tactical.capture":
      return (
        <>
          {actor} took control of{" "}
          {a.detail ? <Named kind="planet" id={a.detail} name={resolvePlanetName(a.detail)} /> : <i>a planet</i>}
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
    case "component.use":
      // Lider / zdolność frakcji / przełom jako akcja komponentu (RULES.md 61.3).
      return (
        <>
          {actor} used{" "}
          {a.detail === "leader" ? (
            <Named kind="leader" id={a.subject ?? ""} name={getLeaderById(a.subject ?? "")?.name ?? prettifyId(a.subject ?? "")} />
          ) : a.detail === "technology" ? (
            <Named kind="tech" id={a.subject ?? ""} name={resolveTechName(a.subject ?? "")} />
          ) : (
            <i>{prettifyId(a.subject ?? "")}</i>
          )}
        </>
      );
    case "promissory.play":
      // Zagrana notka (jawna od chwili zagrania) — RULES.md 61.2.
      return (
        <>
          {actor} played note{" "}
          <Named kind="promissory" id={a.subject ?? ""} name={resolveCardName("CARD_PLAY_PROMISSORY_NOTE", a.subject ?? "")} />
        </>
      );
    case "tech.exhaust":
      return (
        <>
          {actor} exhausted <Named kind="tech" id={a.subject ?? ""} name={resolveTechName(a.subject ?? "")} />
        </>
      );
    case "leader.state":
      return (
        <>
          {actor} {a.detail ?? "updated"}{" "}
          <Named kind="leader" id={a.subject ?? ""} name={getLeaderById(a.subject ?? "")?.name ?? prettifyId(a.subject ?? "")} />
        </>
      );
    case "combat.start":
      return (
        <>
          {battleName(a, ctx)} · {actor} attacks {a.target_id ? target : "an enemy"}
        </>
      );
    case "combat.losses":
      return (
        <>
          {battleName(a, ctx)} · {actor} took losses
        </>
      );
    case "combat.end": {
      const result = a.facts.find((f) => f.type === "battle_result");
      if (!a.subject) {
        // Wpis sprzed nazw bitew (bez miejsca i wyniku).
        return (
          <>
            Battle between {actor}
            {a.target_id && <> and {target}</>} ended
          </>
        );
      }
      return (
        <>
          {battleName(a, ctx)} ended ·{" "}
          {result?.detail === "winner" && result.player_id ? (
            <>{name(ctx, result.player_id)} won</>
          ) : (
            <>draw</>
          )}
        </>
      );
    }
    case "invasion.bombard":
      return (
        <>
          {actor} bombarded{" "}
          {a.subject ? <Named kind="planet" id={a.subject} name={resolvePlanetName(a.subject)} /> : detailSystem(a, ctx)}
        </>
      );
    case "invasion.defense":
      return (
        <>
          Space Cannon Defense
          {a.subject && (
            <> on <Named kind="planet" id={a.subject} name={resolvePlanetName(a.subject)} /></>
          )}{" "}
          · {actor}&apos;s landing
        </>
      );
    case "invasion.establish":
      return (
        <>
          Invasion of {detailSystem(a, ctx)} · {actor} established control
        </>
      );
    case "spacecannon.losses":
      return (
        <>
          Space Cannon fire in {detailSystem(a, ctx)} · {actor} took losses
        </>
      );
    case "combat.retreat_announce":
      return <>{actor} announced a retreat</>;
    case "combat.retreat":
      return (
        <>
          {actor} retreated
          {a.subject && <> to <Named kind="system" id={a.subject} name={ctx.systemName(a.subject)} systemText={ctx.systemHint(a.subject)} /></>}
        </>
      );
    case "invasion.begin":
      return (
        <>
          {actor} began an invasion of {sysNode}
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
    case "transaction.opened":
      return (
        <>
          {actor} sat down to trade with {target}
        </>
      );
    case "transaction.agreed":
      return (
        <>
          {actor} agreed on a deal with {target}
        </>
      );
    case "transaction.closed":
      return (
        <>
          {actor} left the trading table with {target}
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
          <Named kind="objective" id={a.subject ?? ""} name={resolveObjectiveName(a.subject ?? "")} />
        </>
      );
    case "agenda.reveal":
      return (
        <>
          {actor} revealed <b>{resolveAgendaName(a.subject ?? "")}</b>
        </>
      );
    case "agenda.vote":
      return (
        <>
          {actor} cast <b>{a.detail ?? "?"}</b> votes for{" "}
          <b>{agendaOutcomeName(ctx, a.subject)}</b>
        </>
      );
    case "agenda.abstain":
      return <>{actor} abstained</>;
    case "agenda.decide":
      return (
        <>
          {actor} chose <b>{agendaOutcomeName(ctx, a.subject)}</b> (tie)
        </>
      );
    case "agenda.discard":
      return <>{actor} discarded an unresolvable agenda</>;
    case "agenda.next":
      return a.subject === "COMPLETE" ? (
        <>Agendas resolved - planets readied</>
      ) : (
        <>{actor} moved on to the next agenda</>
      );
    case "scoring.finish":
      return <>Scoring finished</>;
    case "scoring.redistribute":
      return <>{actor} redistributed command tokens</>;
    case "explore.draw":
      return (
        <>
          {actor} explored <Named kind="planet" id={a.subject ?? ""} name={resolvePlanetName(a.subject ?? "")} />
        </>
      );
    case "explore.resolve":
      return (
        <>
          {actor} resolved <Named kind="explore" id={a.subject ?? ""} name={exploreCardName(a.subject)} />
        </>
      );
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
  // Show whose fact it is only when it is not the actor's own (battle summary: always — both
  // sides' losses sit side by side).
  const own = fact.player_id === a.actor_id && a.action !== "combat.end";
  const who =
    fact.player_id === null || own ? null : (
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
            {prefix}researched <Named kind="tech" id={fact.value ?? ""} name={resolveTechName(fact.value ?? "")} />
          </>
        ),
      };
    case "ability_used":
      return {
        key,
        tone: "info",
        text: (
          <>
            {prefix}used <b>{resolveEffectName(fact.value ?? "")}</b>
            {fact.detail && <>: {fact.detail}</>}
          </>
        ),
      };
    case "tech_lost":
      return {
        key,
        tone: "bad",
        text: (
          <>
            {prefix}returned <Named kind="tech" id={fact.value ?? ""} name={resolveTechName(fact.value ?? "")} /> to the deck
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
            {prefix}gained <Named kind="planet" id={fact.value ?? ""} name={resolvePlanetName(fact.value ?? "")} />
          </>
        ),
      };
    case "planet_lost":
      return {
        key,
        tone: "bad",
        text: (
          <>
            {prefix}lost <Named kind="planet" id={fact.value ?? ""} name={resolvePlanetName(fact.value ?? "")} />
          </>
        ),
      };
    case "action_card": {
      const card = <Named kind="actionCard" id={fact.value ?? ""} name={resolveCardName("CARD_PLAY_ACTION_CARD", fact.value ?? "")} />;
      return {
        key,
        tone: "card",
        text: fact.player_id ? (
          <>
            {prefix}played {card}
          </>
        ) : (
          <>Action card: {card}</>
        ),
      };
    }
    case "action_card_discarded": {
      const card = <Named kind="actionCard" id={fact.value ?? ""} name={resolveCardName("CARD_PLAY_ACTION_CARD", fact.value ?? "")} />;
      return {
        key,
        tone: "card",
        text: (
          <>
            {prefix}discarded {card}
          </>
        ),
      };
    }
    case "agenda":
      return {
        key,
        tone: "card",
        text: <>Agenda: <Named kind="agenda" id={fact.value ?? ""} name={resolveAgendaName(fact.value ?? "")} /></>,
      };
    case "explore_card":
      return {
        key,
        tone: "card",
        text: (
          <>
            {prefix}revealed <Named kind="explore" id={fact.value ?? ""} name={exploreCardName(fact.value)} />
            {fact.detail && <> ({prettifyId(fact.detail)})</>}
          </>
        ),
      };
    case "relic_fragment":
      return {
        key,
        tone: "card",
        text: (
          <>
            {prefix}kept fragment <Named kind="explore" id={fact.value ?? ""} name={exploreCardName(fact.value)} />
          </>
        ),
      };
    case "promissory_in_play":
      return {
        key,
        tone: "card",
        text: (
          <>
            {prefix}played note{" "}
            <Named kind="promissory" id={fact.value ?? ""} name={resolveCardName("CARD_PLAY_PROMISSORY_NOTE", fact.value ?? "")} />
          </>
        ),
      };
    case "objective_revealed":
      return {
        key,
        tone: "card",
        text: <>Objective revealed: <Named kind="objective" id={fact.value ?? ""} name={resolveObjectiveName(fact.value ?? "")} /></>,
      };
    case "secret_scored":
      return {
        key,
        tone: "good",
        text: (
          <>
            {prefix}scored secret <Named kind="objective" id={fact.value ?? ""} name={resolveObjectiveName(fact.value ?? "")} />
          </>
        ),
      };
    case "commodities":
      return {
        key,
        tone: delta > 0 ? "good" : "bad",
        text: (
          <>
            {prefix}
            {delta > 0 ? "+" : ""}
            {delta} commodities
          </>
        ),
      };
    case "cc": {
      const pool = CC_POOL[fact.value ?? ""] ?? "command";
      return {
        key,
        tone: delta > 0 ? "good" : "info",
        text: (
          <>
            {prefix}
            {delta > 0 ? "+" : ""}
            {delta} {pool} command token{Math.abs(delta) === 1 ? "" : "s"}
          </>
        ),
      };
    }
    case "hand": {
      const what = HAND_NAME[fact.value ?? ""] ?? "cards";
      return {
        key,
        tone: delta > 0 ? "good" : "info",
        text: (
          <>
            {prefix}
            {delta > 0 ? "drew" : "lost"} {Math.abs(delta)} {what}
          </>
        ),
      };
    }
    case "units": {
      const unit = resolveUnitName(fact.value ?? "");
      return {
        key,
        tone: delta > 0 ? "good" : "bad",
        text: (
          <>
            {prefix}
            {delta > 0 ? "+" : ""}
            {delta} {unit}
          </>
        ),
      };
    }
    case "system_token":
      return {
        key,
        tone: "info",
        text: (
          <>
            {prefix}placed a command token in{" "}
            <Named kind="system" id={fact.value ?? ""} name={ctx.systemName(fact.value ?? "")} systemText={ctx.systemHint(fact.value ?? "")} />
          </>
        ),
      };
    case "relic":
      return {
        key,
        tone: fact.detail === "lost" ? "bad" : "card",
        text: (
          <>
            {prefix}
            {fact.detail === "lost" ? "lost relic " : "gained relic "}
            <b>{resolveCardName("CARD_PLAY_RELIC", fact.value ?? "")}</b>
          </>
        ),
      };
    case "frontier_card":
      return {
        key,
        tone: "card",
        text: (
          <>
            {prefix}kept <Named kind="explore" id={fact.value ?? ""} name={exploreCardName(fact.value)} />
          </>
        ),
      };
    case "leader": {
      if (a.action === "leader.state" && fact.value === a.subject) return null;
      return {
        key,
        tone: "info",
        text: (
          <>
            {prefix}
            <Named kind="leader" id={fact.value ?? ""} name={getLeaderById(fact.value ?? "")?.name ?? prettifyId(fact.value ?? "")} />{" "}
            is now {fact.detail ?? "updated"}
          </>
        ),
      };
    }
    case "breakthrough_unlocked":
      return { key, tone: "good", text: <>{prefix}unlocked their breakthrough</> };
    case "strategy_card_gained":
      if (a.action === "strategy.pick") return null;
      return {
        key,
        tone: "info",
        text: (
          <>
            {prefix}took <Named kind="strategy" id={fact.value ?? ""} idMap={ctx.strategyCardIdMap} name={strategyCardName(ctx, fact.value)} />
          </>
        ),
      };
    case "law_enacted":
      return {
        key,
        tone: "card",
        text: (
          <>
            Law in play: <Named kind="agenda" id={fact.value ?? ""} name={resolveAgendaName(fact.value ?? "")} />
            {fact.detail && <> ({agendaOutcomeName(ctx, fact.detail)})</>}
          </>
        ),
      };
    case "rider":
      return {
        key,
        tone: "card",
        text: (
          <>
            {prefix}played{" "}
            <Named kind="actionCard" id={fact.value ?? ""} name={resolveCardName("CARD_PLAY_ACTION_CARD", fact.value ?? "")} />{" "}
            on {agendaOutcomeName(ctx, fact.detail ?? null)}
          </>
        ),
      };
    case "law_repealed":
      return {
        key,
        tone: "bad",
        text: (
          <>
            Law repealed: <Named kind="agenda" id={fact.value ?? ""} name={resolveAgendaName(fact.value ?? "")} />
          </>
        ),
      };
    case "attached": {
      // Karta przy planecie: eksploracja / relikt, notka (Terraform) albo bohater (Geoform) - 62.18.
      const id = fact.value ?? "";
      const leader = getLeaderById(id);
      const note = leader ? undefined : promissoryNotes.find((n) => n.alias === id);
      const card = leader ? (
        <Named kind="leader" id={id} name={leader.name} />
      ) : note ? (
        <Named kind="promissory" id={id} name={note.name} />
      ) : (
        <Named kind="explore" id={id} name={exploreCardName(fact.value)} />
      );
      return {
        key,
        tone: "card",
        text: (
          <>
            {card} attached to{" "}
            <Named kind="planet" id={fact.detail ?? ""} name={resolvePlanetName(fact.detail ?? "")} />
          </>
        ),
      };
    }
    case "faction_token":
    case "faction_token_removed": {
      // Żetony frakcji na mapie (sleeper Titans, RULES.md 61.6): detail = planeta albo "space".
      const where = fact.detail ?? "";
      const kind = prettifyId(fact.value ?? "token");
      const place =
        where && where !== "space" ? (
          <Named kind="planet" id={where} name={resolvePlanetName(where)} />
        ) : (
          <>space</>
        );
      return {
        key,
        tone: fact.type === "faction_token" ? "info" : "bad",
        text:
          fact.type === "faction_token" ? (
            <>
              {prefix}placed a {kind} token on {place}
            </>
          ) : (
            <>
              {kind} token removed from {place}
            </>
          ),
      };
    }
    case "objective_scored":
      if (a.action === "objective.score" && fact.value === a.subject) return null;
      return {
        key,
        tone: "good",
        text: (
          <>
            {prefix}scored <Named kind="objective" id={fact.value ?? ""} name={resolveObjectiveName(fact.value ?? "")} />
          </>
        ),
      };
    case "effect":
      return {
        key,
        tone: "info",
        text: (
          <>
            {prefix}used <b>{resolveEffectName(fact.value ?? "")}</b>
            {fact.detail && <> (active for {describeEffectScope(fact.detail)})</>}
          </>
        ),
      };
    case "speaker":
      if (a.action === "speaker.set") return null;
      return { key, tone: "info", text: <>{who ?? <b>{playerName(ctx, fact.player_id)}</b>} became Speaker</> };
    case "custodians_removed":
      return { key, tone: "good", text: <>The Custodians token was removed from Mecatol Rex</> };
    case "eliminated": {
      // Wyeliminowany gracz znika z listy graczy - nazwa z faktu (gracz albo frakcja).
      const label =
        fact.detail || (fact.value ? prettifyId(fact.value) : playerName(ctx, fact.player_id));
      return { key, tone: "bad", text: <><b>{label}</b> was eliminated from the game</> };
    }
    case "fracture_entered":
      return {
        key,
        tone: "good",
        text: fact.player_id ? (
          <>{<b>{playerName(ctx, fact.player_id)}</b>} brought The Fracture into play</>
        ) : (
          <>The Fracture entered play</>
        ),
      };
    case "tile_replaced": {
      // Nova Seed (Muaat): kafel systemu wymieniony — detail = "<stary kafel>><nowy kafel>".
      const position = fact.value ?? "";
      const oldTile = (fact.detail ?? "").split(">")[0];
      return {
        key,
        tone: "bad",
        text: (
          <>
            <b>{oldTile ? resolveSystemName(oldTile) : position}</b> was replaced by{" "}
            <Named kind="system" id={position} name={ctx.systemName(position)} systemText={ctx.systemHint(position)} />
          </>
        ),
      };
    }
    case "battle_result": {
      // Podsumowanie bitwy: zwycięzca w nagłówku, tu długość walki.
      const rounds = `${delta} round${delta === 1 ? "" : "s"}`;
      return {
        key,
        tone: fact.detail === "winner" ? "good" : "info",
        text: fact.detail === "winner" ? <>Victory after {rounds}</> : <>Draw after {rounds}</>,
      };
    }
    case "winner":
      return { key, tone: "good", text: <>{<b>{playerName(ctx, fact.player_id)}</b>} won the game</> };
    default:
      return null;
  }
}

const CC_POOL: Record<string, string> = {
  tactical_cc: "tactical",
  fleet_cc: "fleet",
  strategic_cc: "strategy",
};

const HAND_NAME: Record<string, string> = {
  action_cards: "action cards",
  promissory_notes: "promissory notes",
  secret_objectives: "secret objectives",
};

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
