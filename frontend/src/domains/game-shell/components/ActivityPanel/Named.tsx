import type { ReactNode } from "react";
import { Tooltip } from "@/ds";
import { agendas } from "@/entities/data/agendas";
import { promissoryNotes } from "@/entities/data/promissoryNotes";
import { getActionCard } from "@/entities/lookup/actionCards";
import { getExploration } from "@/entities/lookup/explorations";
import { getLeaderById } from "@/entities/lookup/leaders";
import { getPlanetData } from "@/entities/lookup/planets";
import { getPublicObjective } from "@/entities/lookup/publicObjectives";
import { getSecretObjectiveData } from "@/entities/lookup/secretObjectives";
import { getStrategyCardByInitiative } from "@/entities/lookup/strategyCards";
import { getTechData } from "@/entities/lookup/tech";
import { prettifyId } from "../GameEventPanel/eventFormatting";
import classes from "./Named.module.css";

export type NamedKind =
  | "actionCard"
  | "agenda"
  | "explore"
  | "tech"
  | "objective"
  | "strategy"
  | "planet"
  | "leader"
  | "promissory"
  | "system";

type Hint = { name: string; meta?: string; lines: string[] };

const agendaByAlias = new Map(agendas.map((a) => [a.alias, a]));
const promissoryByAlias = new Map(promissoryNotes.map((n) => [n.alias, n]));

function clean(lines: (string | undefined | null)[]): string[] {
  return lines.map((l) => l?.trim() ?? "").filter((l) => l.length > 0);
}

function hintFor(
  kind: NamedKind,
  id: string,
  extra?: { idMap?: Record<number, string>; systemText?: string },
): Hint | null {
  switch (kind) {
    case "actionCard": {
      const c = getActionCard(id);
      if (!c) return null;
      return {
        name: c.name,
        meta: c.window ? `Action card · ${c.window}` : "Action card",
        lines: clean([c.text]),
      };
    }
    case "agenda": {
      const a = agendaByAlias.get(id);
      if (!a) return null;
      return {
        name: a.name,
        meta: `Agenda · ${a.type}`,
        lines: clean([a.target, a.text1, a.text2]),
      };
    }
    case "explore": {
      const e = getExploration(id);
      if (!e) return null;
      return {
        name: e.name,
        meta: e.type ? `Exploration · ${prettifyId(e.type)}` : "Exploration",
        lines: clean([e.text]),
      };
    }
    case "tech": {
      const t = getTechData(id);
      if (!t) return null;
      return {
        name: t.name,
        meta: clean([
          "Technology",
          t.types?.[0] ? prettifyId(t.types[0].toLowerCase()) : null,
          t.requirements ? `Prerequisites: ${t.requirements}` : null,
        ]).join(" · "),
        lines: clean([t.text]),
      };
    }
    case "objective": {
      const o = getPublicObjective(id) ?? getSecretObjectiveData(id);
      if (!o) return null;
      return {
        name: o.name,
        meta: `Objective · ${o.points} VP · ${o.phase}`,
        lines: clean([o.text]),
      };
    }
    case "strategy": {
      const card = getStrategyCardByInitiative(Number(id), extra?.idMap);
      if (!card) return null;
      return {
        name: card.name,
        meta: `Strategy card · initiative ${card.initiative}`,
        lines: clean([
          ...card.primaryTexts.map((t) => `Primary: ${t}`),
          ...card.secondaryTexts.map((t) => `Secondary: ${t}`),
        ]),
      };
    }
    case "planet": {
      const p = getPlanetData(id);
      if (!p) return null;
      const traits = (p.planetTypes ?? (p.planetType ? [p.planetType] : [])).join(", ");
      return {
        name: p.name,
        meta: `Planet · ${p.resources} resources / ${p.influence} influence`,
        lines: clean([
          traits ? `Type: ${prettifyId(traits.toLowerCase())}` : null,
          p.techSpecialties?.length
            ? `Tech specialty: ${p.techSpecialties.join(", ")}`
            : null,
          p.legendaryAbilityName
            ? `${p.legendaryAbilityName}: ${p.legendaryAbilityText ?? ""}`
            : null,
        ]),
      };
    }
    case "leader": {
      const l = getLeaderById(id);
      if (!l) return null;
      return {
        name: l.name,
        meta: `${prettifyId(l.type.toLowerCase())}${l.title ? ` · ${l.title}` : ""}`,
        lines: clean([
          l.abilityWindow ? `${l.abilityWindow}:` : null,
          l.abilityText,
          l.unlockCondition ? `Unlock: ${l.unlockCondition}` : null,
        ]),
      };
    }
    case "promissory": {
      const n = promissoryByAlias.get(id);
      if (!n) return null;
      return { name: n.name, meta: "Promissory note", lines: clean([n.text]) };
    }
    case "system":
      return extra?.systemText
        ? { name: "", lines: clean([extra.systemText]) }
        : null;
  }
}

function HintBody({ hint }: { hint: Hint }) {
  return (
    <div className={classes.hint}>
      {hint.name && <b className={classes.title}>{hint.name}</b>}
      {hint.meta && <small className={classes.meta}>{hint.meta}</small>}
      {hint.lines.map((line, index) => (
        <p key={index} className={classes.line}>
          {line}
        </p>
      ))}
    </div>
  );
}

/**
 * A name from the game (card, tech, planet, objective…) that explains itself on
 * hover: type, cost/window and the rules text, read from the bundled data.
 * Falls back to the plain name when nothing is known about the id.
 */
export function Named({
  kind,
  id,
  name,
  idMap,
  systemText,
  children,
}: {
  kind: NamedKind;
  id: string;
  /** Display name; defaults to the one in the data. */
  name?: string;
  idMap?: Record<number, string>;
  systemText?: string;
  children?: ReactNode;
}) {
  const hint = hintFor(kind, id, { idMap, systemText });
  const label = children ?? name ?? hint?.name ?? prettifyId(id);
  if (!hint) return <i>{label}</i>;
  return (
    <Tooltip
      label={<HintBody hint={hint} />}
      multiline
      withArrow
      openDelay={200}
      maw={320}
      events={{ hover: true, focus: true, touch: true }}
    >
      <i className={classes.named} tabIndex={0}>
        {label}
      </i>
    </Tooltip>
  );
}
