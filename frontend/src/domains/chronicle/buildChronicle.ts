// Kronika Imperium: zamienia feed Activity (core/activity.py) na rozdziały „księgi".
// Czysta warstwa prezentacyjna — nic nie liczy z reguł, tylko czyta to, co silnik już zapisał
// (fakty wpisów), i dokłada tekst z `chronicleLore.ts` oraz opisy bitew z `battleLore.ts`.
// Każdy wpis niesie DWIE warstwy: opowieść (`text`) i suche fakty (`facts`) — „co dokładnie
// się stało" — żeby lore nigdy nie zasłaniało prawdy o zdarzeniu.

import type { ActivityEntry, ActivityFact, ActivityPlayer } from "@/api/useBoardEditor";
import { getPlanetData } from "@/entities/lookup/planets";
import { getFactionLore } from "@/entities/lore/factionLore";
import { getLeaderById } from "@/entities/lookup/leaders";
import {
  prettifyId,
  resolveAgendaName,
  resolveCardName,
  resolveObjectiveName,
  resolvePlanetName,
  resolveTechName,
  resolveUnitName,
} from "../game-shell/components/GameEventPanel/eventFormatting";
import { describeBattle } from "@/entities/lore/battleLore";
import {
  CHRONICLERS,
  OPENERS,
  FACTION_EPITHET,
  KIND_LABEL,
  MINOR_KINDS,
  POOLS,
  REPEAL,
  STANDINGS_LEAD,
  STANDINGS_TIE,
  type OpenerTheme,
  type ChronicleKind,
  type Pool,
} from "@/entities/lore/chronicleLore";
import { lookupLoreOr } from "@/entities/lore/lookupLore";

/** Cytat pod wpisem wraz z autorem — zawsze wiadomo, kto to mówi. */
export type ChronicleQuote = { text: string; author: string };

export type ChronicleEntry = {
  id: string;
  seq: number;
  kind: ChronicleKind;
  label: string;
  round: number;
  /** Opowieść (tekst kronikarski). */
  text: string;
  /** Motto/cytat z lore planety albo systemu (jeśli jest). */
  epigraph: ChronicleQuote | null;
  /** Miejsce, jeśli zdarzenie ma je na mapie (nazwa systemu/planety). */
  place: string | null;
  /** Gracze, których to dotyczy (id) — do herbów. */
  actors: string[];
  /** Suche fakty: „co dokładnie się stało". */
  facts: string[];
  /** Kluczowa nazwa zdarzenia (prawo, relikt, cel) do zdań otwierających następny rozdział. */
  detail: string | null;
  minor: boolean;
};

export type ChronicleStanding = { playerId: string; vp: number };

export type ChronicleChapter = {
  round: number;
  title: string;
  opener: ChronicleQuote;
  entries: ChronicleEntry[];
  /** Stan wyścigu po tym rozdziale (malejąco wg VP). */
  standings: ChronicleStanding[];
  closing: string | null;
};

export type ChronicleSource = {
  entries: ActivityEntry[];
  players: Record<string, ActivityPlayer>;
  /** Wpisy o `seq` większym są cofnięte (gałąź redo) — pomijamy. */
  currentSeq: number | null;
};

export type ChronicleNames = {
  systemName: (position: string) => string;
};

function hash(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function fill(pool: Pool, seed: string, vars: Record<string, string>): string {
  const template = pool[hash(seed) % pool.length];
  const text = template.replace(/\{(\w+)\}/g, (_, key: string) => vars[key] ?? "");
  // Zdanie zawsze zaczyna się wielką literą (przydomki są pisane małą: „the Arborec…").
  return text.replace(/(^|[.!?]\s+)([a-z])/g, (_, lead: string, c: string) => lead + c.toUpperCase());
}

/** Pierwsze zdanie tekstu (motto); za długie tnie na granicy zdania. */
function firstSentence(text: string | null | undefined): string | null {
  const clean = (text ?? "").replace(/^\*+|\*+$/g, "").trim();
  if (!clean) return null;
  const first = clean.match(/^.+?[.!?](\s|$)/)?.[0].trim() ?? clean;
  return first.length > 220 ? `${first.slice(0, 217).trimEnd()}…` : first;
}

const CUSTODIAN = "A Custodian of Mecatol Rex";

type Ctx = {
  source: ChronicleSource;
  /** Cytat frakcji gracza (z `factionLore.ts`) z podpisem autora; null, gdy brak. */
  quoteOf: (pid: string | null | undefined) => ChronicleQuote | null;
  names: ChronicleNames;
  nm: (pid: string | null | undefined) => string;
  ep: (pid: string | null | undefined) => string;
};

function makeCtx(source: ChronicleSource, names: ChronicleNames): Ctx {
  const nm = (pid: string | null | undefined): string => {
    if (!pid) return "Someone";
    const p = source.players[pid];
    if (!p) return prettifyId(pid);
    return (
      p.faction_name?.trim() ||
      p.display_name.trim() ||
      (p.faction ? prettifyId(p.faction) : prettifyId(pid))
    );
  };
  const ep = (pid: string | null | undefined): string => {
    const faction = pid ? source.players[pid]?.faction : null;
    return (faction && FACTION_EPITHET[faction]) || nm(pid);
  };
  const quoteOf = (pid: string | null | undefined): ChronicleQuote | null => {
    const faction = pid ? source.players[pid]?.faction : null;
    const lore = faction ? getFactionLore(faction) : undefined;
    const text = lore?.quote?.replace(/^["“”]+|["“”]+$/g, "").trim();
    if (!text) return null;
    return { text, author: lore?.quoteAuthor?.replace(/^[-—\s]+/, "").trim() || nm(pid) };
  };
  return { source, quoteOf, names, nm, ep };
}

const unitList = (facts: ActivityFact[], pid: string | null, sign: -1 | 1): string => {
  const parts = facts
    .filter((f) => f.type === "units" && f.player_id === pid && (f.delta ?? 0) * sign > 0)
    .map((f) => `${Math.abs(f.delta ?? 0)} ${resolveUnitName(f.value ?? "")}`);
  return parts.join(", ");
};

/** Zdarzenia jednego wpisu feedu (0..n wpisów kroniki). */
function entriesFrom(entry: ActivityEntry, ctx: Ctx, seenLeaders: Set<string>): ChronicleEntry[] {
  const a = entry.activity;
  const out: ChronicleEntry[] = [];
  let idx = 0;
  const push = (
    kind: ChronicleKind,
    text: string,
    extra: Partial<Pick<ChronicleEntry, "epigraph" | "place" | "actors" | "facts" | "detail">> = {},
  ) => {
    out.push({
      id: `${entry.seq}-${idx++}`,
      seq: entry.seq,
      kind,
      label: KIND_LABEL[kind],
      round: a.round,
      text,
      epigraph: extra.epigraph ?? null,
      place: extra.place ?? null,
      actors: extra.actors ?? [],
      facts: extra.facts ?? [],
      detail: extra.detail ?? null,
      minor: MINOR_KINDS.has(kind),
    });
  };
  const planetQuote = (text: string | null | undefined): ChronicleQuote | null => {
    const quote = firstSentence(text);
    return quote ? { text: quote, author: CUSTODIAN } : null;
  };
  const seed = (suffix: string) => `${entry.seq}|${suffix}`;
  const vpOf = (pid: string | null) =>
    a.facts.filter((f) => f.type === "vp" && f.player_id === pid).reduce((s, f) => s + (f.delta ?? 0), 0);

  // ---- bitwa -------------------------------------------------------------
  if (a.action === "combat.end" && a.subject && a.actor_id && a.target_id) {
    const result = a.facts.find((f) => f.type === "battle_result");
    const winnerId = result?.detail === "winner" ? result.player_id : null;
    const ground = a.subject !== "space";
    const place = ground ? resolvePlanetName(a.subject) : ctx.names.systemName(a.detail ?? "");
    const lost = (pid: string) =>
      a.facts
        .filter((f) => f.type === "units" && f.player_id === pid && (f.delta ?? 0) < 0)
        .reduce((s, f) => s + Math.abs(f.delta ?? 0), 0);
    const types = (pid: string) =>
      Object.fromEntries(
        a.facts
          .filter((f) => f.type === "units" && f.player_id === pid && (f.delta ?? 0) < 0)
          .map((f) => [f.value ?? "", Math.abs(f.delta ?? 0)]),
      );
    const rounds = result?.delta ?? 1;
    const lore = describeBattle({
      kind: ground ? "ground" : "space",
      where: place,
      attacker: ctx.nm(a.actor_id),
      defender: ctx.nm(a.target_id),
      winner: winnerId === a.actor_id ? "attacker" : winnerId === a.target_id ? "defender" : null,
      rounds,
      attackerLost: lost(a.actor_id),
      defenderLost: lost(a.target_id),
      attackerTypes: types(a.actor_id),
      defenderTypes: types(a.target_id),
      typeName: resolveUnitName,
      seed: entry.seq,
    });
    const planet = ground ? getPlanetData(a.subject) : undefined;
    push("battle", lore.text, {
      place,
      epigraph: planetQuote(lookupLoreOr("planet", planet?.id, planet?.flavourText)) ?? ctx.quoteOf(winnerId ?? a.actor_id),
      actors: [a.actor_id, a.target_id],
      facts: [
        `${ground ? "Ground battle for" : "Space battle of"} ${place} (round ${a.round})`,
        `Attacker: ${ctx.nm(a.actor_id)} · Defender: ${ctx.nm(a.target_id)}`,
        winnerId ? `Winner: ${ctx.nm(winnerId)} after ${rounds} round${rounds === 1 ? "" : "s"}` : `Draw after ${rounds} round${rounds === 1 ? "" : "s"}`,
        `${ctx.nm(a.actor_id)} lost: ${unitList(a.facts, a.actor_id, -1) || "nothing"}`,
        `${ctx.nm(a.target_id)} lost: ${unitList(a.facts, a.target_id, -1) || "nothing"}`,
      ],
    });
    return out;
  }

  // ---- planety: podbój / kolonia ----------------------------------------
  for (const gain of a.facts.filter((f) => f.type === "planet_gained" && f.value)) {
    const planetId = gain.value ?? "";
    const taker = gain.player_id;
    const loss = a.facts.find(
      (f) => f.type === "planet_lost" && f.value === planetId && f.player_id !== taker,
    );
    const planet = getPlanetData(planetId);
    const planetName = resolvePlanetName(planetId);
    const home = loss ? ctx.source.players[loss.player_id ?? ""]?.faction : null;
    const isHome = !!loss && !!home && planet?.factionHomeworld === home;
    const kind: ChronicleKind = loss ? (isHome ? "homeworld" : "conquest") : "settle";
    const vars = {
      A: ctx.nm(taker),
      Ae: ctx.ep(taker),
      B: ctx.nm(loss?.player_id),
      Be: ctx.ep(loss?.player_id),
      planet: planetName,
    };
    push(kind, fill(POOLS[kind], seed(`${kind}|${planetId}`), vars), {
      place: planetName,
      epigraph: planetQuote(lookupLoreOr("planet", planet?.id, planet?.flavourText)) ?? ctx.quoteOf(taker),
      actors: [taker, loss?.player_id].filter((x): x is string => !!x),
      facts: [
        loss
          ? `${ctx.nm(taker)} took ${planetName} from ${ctx.nm(loss.player_id)}`
          : `${ctx.nm(taker)} gained ${planetName}`,
        ...(isHome ? [`${planetName} is the homeworld of ${ctx.nm(loss?.player_id)}`] : []),
        `Round ${a.round}`,
      ],
    });
  }

  // ---- punktowane cele ---------------------------------------------------
  const scored = new Set<string>();
  const score = (objectiveId: string, pid: string | null) => {
    if (!pid || scored.has(`${pid}|${objectiveId}`)) return;
    scored.add(`${pid}|${objectiveId}`);
    const name = resolveObjectiveName(objectiveId);
    const vp = vpOf(pid);
    push(
      "score",
      fill(POOLS.score, seed(`score|${objectiveId}`), {
        A: ctx.nm(pid),
        Ae: ctx.ep(pid),
        obj: name,
      }),
      {
        detail: name,
        actors: [pid],
        facts: [
          `${ctx.nm(pid)} scored “${name}”${vp ? ` (${vp > 0 ? "+" : ""}${vp} VP)` : ""}`,
          `Round ${a.round}`,
        ],
      },
    );
  };
  if (a.action === "objective.score" && a.subject) score(a.subject, a.actor_id);
  for (const f of a.facts) {
    if ((f.type === "objective_scored" || f.type === "secret_scored") && f.value) {
      score(f.value, f.player_id);
    }
  }

  // ---- Rada: prawa i agendy ---------------------------------------------
  if (a.action === "agenda.reveal" && a.subject) {
    push(
      "agenda",
      fill(POOLS.agenda, seed("agenda"), { law: resolveAgendaName(a.subject) }),
      { facts: [`Agenda revealed: ${resolveAgendaName(a.subject)}`, `Round ${a.round}`] },
    );
  }
  for (const f of a.facts) {
    if (f.type === "law_enacted" && f.value) {
      const law = resolveAgendaName(f.value);
      push("law", fill(POOLS.law, seed(`law|${f.value}`), { law }), {
        detail: law,
        facts: [`Law enacted: ${law}`, ...(f.detail ? [`Outcome: ${prettifyId(f.detail)}`] : []), `Round ${a.round}`],
      });
    } else if (f.type === "law_repealed" && f.value) {
      const law = resolveAgendaName(f.value);
      push("law", fill(REPEAL, seed(`repeal|${f.value}`), { law }), {
        facts: [`Law repealed: ${law}`, `Round ${a.round}`],
      });
    }
  }

  // ---- reszta faktów -----------------------------------------------------
  for (const f of a.facts) {
    const pid = f.player_id;
    const base = { A: ctx.nm(pid), Ae: ctx.ep(pid) };
    switch (f.type) {
      case "tech":
        push(
          "tech",
          fill(POOLS.tech, seed(`tech|${f.value}`), { ...base, tech: resolveTechName(f.value ?? "") }),
          { actors: pid ? [pid] : [], facts: [`${base.A} researched ${resolveTechName(f.value ?? "")}`, `Round ${a.round}`] },
        );
        break;
      case "relic":
        if (f.detail === "lost") break;
        push(
          "relic",
          fill(POOLS.relic, seed(`relic|${f.value}`), {
            ...base,
            relic: resolveCardName("CARD_PLAY_RELIC", f.value ?? ""),
          }),
          {
            detail: resolveCardName("CARD_PLAY_RELIC", f.value ?? ""),
            actors: pid ? [pid] : [],
            facts: [`${base.A} gained the relic ${resolveCardName("CARD_PLAY_RELIC", f.value ?? "")}`, `Round ${a.round}`],
          },
        );
        break;
      case "leader": {
        const leader = getLeaderById(f.value ?? "");
        const name = leader?.name ?? prettifyId(f.value ?? "");
        if (f.detail === "purged" && leader?.type === "hero") {
          push("hero", fill(POOLS.hero, seed(`hero|${f.value}`), { ...base, leader: name }), {
            epigraph: ctx.quoteOf(pid),
            actors: pid ? [pid] : [],
            facts: [`${base.A} used the hero ${name}`, `Round ${a.round}`],
          });
        } else if (f.detail === "unlocked" && !seenLeaders.has(f.value ?? "")) {
          seenLeaders.add(f.value ?? "");
          push("leader", fill(POOLS.leader, seed(`leader|${f.value}`), { ...base, leader: name }), {
            actors: pid ? [pid] : [],
            facts: [`${base.A} unlocked ${leader?.type ?? "leader"} ${name}`, `Round ${a.round}`],
          });
        }
        break;
      }
      case "custodians_removed":
        push("throne", fill(POOLS.throne, seed("throne"), { A: ctx.nm(a.actor_id), Ae: ctx.ep(a.actor_id) }), {
          place: "Mecatol Rex",
          epigraph: ctx.quoteOf(a.actor_id),
          actors: a.actor_id ? [a.actor_id] : [],
          facts: [`${ctx.nm(a.actor_id)} removed the Custodians token from Mecatol Rex`, `Round ${a.round}`],
        });
        break;
      case "eliminated": {
        const label = f.detail || (f.value ? prettifyId(f.value) : ctx.nm(pid));
        push("fall", fill(POOLS.fall, seed(`fall|${label}`), { A: label, Ae: ctx.ep(pid) === ctx.nm(pid) ? label : ctx.ep(pid) }), {
          actors: pid ? [pid] : [],
          facts: [`${label} was eliminated`, `Round ${a.round}`],
        });
        break;
      }
      case "fracture_entered":
        push("fracture", fill(POOLS.fracture, seed("fracture"), base), {
          actors: pid ? [pid] : [],
          facts: [`${base.A} brought the Fracture into play`, `Round ${a.round}`],
        });
        break;
      case "tile_replaced": {
        const place = ctx.names.systemName(f.value ?? "");
        push("supernova", fill(POOLS.supernova, seed(`nova|${f.value}`), { ...base, system: place }), {
          place,
          actors: a.actor_id ? [a.actor_id] : [],
          facts: [`System at position ${f.value} was replaced (${f.detail ?? "Nova Seed"})`, `Round ${a.round}`],
        });
        break;
      }
      case "speaker":
        if (a.action === "speaker.set") break;
        push("speaker", fill(POOLS.speaker, seed(`speaker|${pid}`), base), {
          actors: pid ? [pid] : [],
          facts: [`${base.A} became Speaker`, `Round ${a.round}`],
        });
        break;
      case "winner":
        push("victory", fill(POOLS.victory, seed("victory"), base), {
          epigraph: ctx.quoteOf(pid),
          actors: pid ? [pid] : [],
          facts: [`${base.A} won the game`, `Round ${a.round}`],
        });
        break;
      default:
        break;
    }
  }

  // ---- umowy -------------------------------------------------------------
  if ((a.action === "transaction" || a.action === "transaction.agreed") && a.actor_id && a.target_id) {
    push(
      "deal",
      fill(POOLS.deal, seed("deal"), {
        A: ctx.nm(a.actor_id),
        Ae: ctx.ep(a.actor_id),
        B: ctx.nm(a.target_id),
        Be: ctx.ep(a.target_id),
      }),
      {
        actors: [a.actor_id, a.target_id],
        facts: [`${ctx.nm(a.actor_id)} and ${ctx.nm(a.target_id)} agreed on a deal`, `Round ${a.round}`],
      },
    );
  }
  return out;
}

const THEME_PRIORITY: { theme: OpenerTheme; kinds: ChronicleKind[] }[] = [
  { theme: "throne", kinds: ["throne"] },
  { theme: "fall", kinds: ["fall"] },
  { theme: "homeworld", kinds: ["homeworld"] },
  { theme: "hero", kinds: ["hero", "fracture", "supernova"] },
  { theme: "war", kinds: ["battle", "conquest"] },
  { theme: "law", kinds: ["law"] },
  { theme: "relic", kinds: ["relic"] },
  { theme: "score", kinds: ["score"] },
];

/** Opowieść zaczyna się od tego, co NAJWAŻNIEJSZEGO wydarzyło się w poprzednim rozdziale. */
function openerFor(
  round: number,
  previous: ChronicleChapter | null,
  ctx: Ctx,
  used: Set<string>,
): ChronicleQuote {
  const major = previous?.entries.filter((e) => !e.minor && e.kind !== "prologue") ?? [];
  const found = THEME_PRIORITY.find((t) => major.some((e) => t.kinds.includes(e.kind)));
  const theme: OpenerTheme = previous === null ? "start" : (found?.theme ?? "quiet");
  const kinds = found?.kinds ?? [];
  const entry = [...major].reverse().find((e) => kinds.includes(e.kind));
  const battles = major.filter((e) => e.kind === "battle").length;
  const lead = previous?.standings[0];
  const vars: Record<string, string> = {
    A: ctx.nm(entry?.actors[0]),
    B: ctx.nm(entry?.actors[1]),
    place: entry?.place ?? "the Rim",
    n: String(battles),
    detail: entry?.detail ?? "",
    lead: lead ? ctx.nm(lead.playerId) : "No one",
    vp: String(lead?.vp ?? 0),
  };
  // Kronikarz pasujący do tematu; nie powtarzamy, dopóki są wolni, potem po kolei.
  const fits = CHRONICLERS.filter((c) => c.themes.includes(theme) && !used.has(c.name));
  const free = CHRONICLERS.filter((c) => !used.has(c.name));
  const chronicler =
    fits[0] ?? free[0] ?? CHRONICLERS[(Math.max(round, 1) - 1) % CHRONICLERS.length];
  used.add(chronicler.name);
  return {
    text: fill(OPENERS[theme], `opener|${round}|${theme}`, vars),
    author: `${chronicler.name}, ${chronicler.title}`,
  };
}

function closingFor(standings: ChronicleStanding[], ctx: Ctx, round: number): string | null {
  if (standings.length === 0 || standings[0].vp <= 0) return null;
  const lead = standings[0];
  const tied = standings.filter((s) => s.vp === lead.vp);
  if (tied.length > 1) return fill(STANDINGS_TIE, `tie|${round}`, { n: String(lead.vp) });
  return fill(STANDINGS_LEAD, `lead|${round}`, { A: ctx.nm(lead.playerId), n: String(lead.vp) });
}

/** Buduje księgę: rozdział na rundę, wpisy chronologicznie, stan wyścigu po każdym rozdziale. */
export function buildChronicle(source: ChronicleSource, names: ChronicleNames): ChronicleChapter[] {
  const ctx = makeCtx(source, names);
  const visible = source.entries
    .filter(
      (e) =>
        e.activity.kind !== "godmode" && (source.currentSeq === null || e.seq <= source.currentSeq),
    )
    .sort((x, y) => x.seq - y.seq);

  const vp: Record<string, number> = {};
  const seenLeaders = new Set<string>();
  const byRound = new Map<number, ChronicleEntry[]>();
  const standingsAt = new Map<number, ChronicleStanding[]>();

  for (const entry of visible) {
    const round = entry.activity.round;
    for (const f of entry.activity.facts) {
      if (f.type === "vp" && f.player_id) vp[f.player_id] = (vp[f.player_id] ?? 0) + (f.delta ?? 0);
    }
    const events = entriesFrom(entry, ctx, seenLeaders);
    if (events.length > 0) byRound.set(round, [...(byRound.get(round) ?? []), ...events]);
    standingsAt.set(
      round,
      Object.entries(vp)
        .map(([playerId, points]) => ({ playerId, vp: points }))
        .sort((x, y) => y.vp - x.vp),
    );
  }

  const chapters: ChronicleChapter[] = [...byRound.keys()]
    .sort((x, y) => x - y)
    .map((round) => {
      const standings = standingsAt.get(round) ?? [];
      return {
        round,
        title: `Round ${round}`,
        opener: { text: "", author: "" },
        entries: byRound.get(round) ?? [],
        standings,
        closing: closingFor(standings, ctx, round),
      };
    });

  // Zdania otwierające zależą od POPRZEDNIEGO rozdziału, więc liczymy je po zbudowaniu wszystkich.
  const used = new Set<string>();
  chapters.forEach((chapter, i) => {
    chapter.opener = openerFor(chapter.round, i === 0 ? null : chapters[i - 1], ctx, used);
  });

  // Prolog: pierwszy rozdział zaczyna się od zebrania domów przy stole.
  const houses = Object.values(source.players).filter((p) => p.faction).length;
  if (chapters.length > 0 && houses > 0) {
    chapters[0].entries.unshift({
      id: "prologue",
      seq: -1,
      kind: "prologue",
      label: KIND_LABEL.prologue,
      round: chapters[0].round,
      text: fill(POOLS.prologue, "prologue", { n: String(houses) }),
      epigraph: null,
      place: null,
      actors: Object.keys(source.players).filter((id) => source.players[id].faction),
      facts: [`${houses} houses at the table`],
      detail: null,
      minor: false,
    });
  }
  return chapters;
}
