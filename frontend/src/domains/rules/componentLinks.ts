/**
 * In-game component links in rules content.
 *
 * The tirules2 dump links many component names (faction abilities, technologies, leaders,
 * promissory notes, units…) to the Twilight Imperium fandom wiki, e.g.
 * `https://twilight-imperium.fandom.com/wiki/The_Nekro_Virus#Faction_Technologies:~:text=Valefar%20Assimilator`.
 * The game already ships the full text of every such component (AsyncTI4 static data), so
 * instead of sending the player to an external site the rules viewer resolves the link to the
 * component and shows its in-game card (`ComponentCard` / `UnitDetailsCard`).
 *
 * Resolution: only links with a URL text fragment (`:~:text=`) name a single component; the name
 * comes from the fragment, falling back to the link label. It is matched case-insensitively against official-source components; when no
 * exact name exists, names that extend it by a word ("Valefar Assimilator" → X and Y) match.
 * The wiki page title (faction name) narrows ambiguous matches to that faction.
 */

import type { ComponentKind } from "@/domains/cards/components/ComponentInfo";
import { abilities } from "@/entities/data/abilities";
import { actionCards } from "@/entities/data/actionCards";
import { agendas } from "@/entities/data/agendas";
import { breakthroughs } from "@/entities/data/breakthroughs";
import { leaders } from "@/entities/data/leaders";
import { planets } from "@/entities/data/planets";
import { isInActiveDeck, isOfficialSource } from "@/entities/data/officialSources";
import { promissoryNotes } from "@/entities/data/promissoryNotes";
import { relics } from "@/entities/data/relics";
import { techs } from "@/entities/data/tech";
import { units } from "@/entities/data/units";

/** Kind of an in-game component a rules link can point to (`unit` = `UnitDetailsCard`). */
export type RuleComponentKind = ComponentKind | "unit";

export type RuleComponentRef = {
  kind: RuleComponentKind;
  id: string;
  /** Full display name from the game data. */
  name: string;
};

type Entry = RuleComponentRef & { faction?: string };

/** `https://twilight-imperium.fandom.com/wiki/<page>[#<anchor>][:~:text=<name>]`. */
const WIKI_URL_RE = /^https?:\/\/twilight-imperium\.fandom\.com\/wiki\/([^#?]*)(?:#(.*))?$/;

/** Normalizes a name for matching: lower case, unified apostrophes/dashes, single spaces. */
export function normalizeName(name: string): string {
  return name
    .toLowerCase()
    .replace(/[‘’`]/g, "'")
    .replace(/[–—]/g, "-")
    .replace(/\s+/g, " ")
    .trim();
}

/** Letters and digits only — for comparing faction ids with wiki page titles. */
function compact(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function safeDecode(text: string): string {
  try {
    return decodeURIComponent(text);
  } catch {
    return text;
  }
}

let index: Map<string, Entry[]> | null = null;

function buildIndex(): Map<string, Entry[]> {
  const map = new Map<string, Entry[]>();
  const add = (name: string | undefined, entry: Entry) => {
    if (!name) return;
    const key = normalizeName(name);
    const list = map.get(key) ?? [];
    // The same component may exist in several official sources (base + codex errata) under
    // different ids: the later one (newer printing) replaces the earlier.
    const same = list.findIndex((e) => e.kind === entry.kind && e.faction === entry.faction);
    if (same >= 0) list[same] = entry;
    else list.push(entry);
    map.set(key, list);
  };

  for (const a of abilities) {
    if (isOfficialSource(a.source)) add(a.name, { kind: "ability", id: a.id, name: a.name, faction: a.faction });
  }
  for (const t of techs) {
    if (isOfficialSource(t.source)) add(t.name, { kind: "tech", id: t.alias, name: t.name, faction: t.faction });
  }
  for (const b of breakthroughs) {
    if (!isOfficialSource(b.source)) continue;
    const entry: Entry = { kind: "breakthrough", id: b.alias, name: b.name, faction: b.faction };
    add(b.name, entry);
    if (b.displayName && normalizeName(b.displayName) !== normalizeName(b.name)) add(b.displayName, entry);
  }
  for (const l of leaders) {
    if (!isOfficialSource(l.source)) continue;
    const entry: Entry = { kind: "leader", id: l.id, name: l.name, faction: l.faction };
    add(l.name, entry);
    // Hero abilities are named in rulings by their ability name ("Benediction"); some carry a
    // subtitle after a colon in the data ("Benediction: …").
    if (l.abilityName) {
      add(l.abilityName, entry);
      const head = l.abilityName.split(":")[0];
      if (head !== l.abilityName) add(head, entry);
    }
  }
  for (const p of promissoryNotes) {
    if (isOfficialSource(p.source)) add(p.name, { kind: "promissory", id: p.alias, name: p.name, faction: p.faction });
  }
  for (const u of units) {
    if (isOfficialSource(u.source)) add(u.name, { kind: "unit", id: u.id, name: u.name, faction: u.faction });
  }
  for (const p of planets) {
    // Only real, official planets (skips "(Plus)" homebrew copies and `[x.y.z]` placeholders).
    if (p.source && isOfficialSource(p.source) && !p.name.startsWith("[")) {
      add(p.name, { kind: "planet", id: p.id, name: p.name });
    }
  }
  for (const r of relics) {
    if (isOfficialSource(r.source)) add(r.name, { kind: "relic", id: r.alias, name: r.name });
  }
  for (const c of actionCards) {
    if (isInActiveDeck("actionCard", c.alias)) add(c.name, { kind: "actionCard", id: c.alias, name: c.name });
  }
  for (const g of agendas) {
    if (isInActiveDeck("agenda", g.alias)) add(g.name, { kind: "agenda", id: g.alias, name: g.name });
  }
  return map;
}

function getIndex(): Map<string, Entry[]> {
  index ??= buildIndex();
  return index;
}

/** Keeps the candidates of the faction named by the wiki page, when any of them match it. */
function narrowByPage(candidates: Entry[], page: string): Entry[] {
  if (candidates.length < 2 || !page) return candidates;
  const title = compact(safeDecode(page));
  const ofPage = candidates.filter((c) => {
    if (!c.faction) return false;
    const faction = compact(c.faction);
    // Faction variants carry a one-letter suffix (`keleresm`, `keleresx`…).
    return title.includes(faction) || (faction.length > 5 && title.includes(faction.slice(0, -1)));
  });
  return ofPage.length > 0 ? ofPage : candidates;
}

/** Wiki page section (URL anchor) => the component kind it lists. */
const SECTION_KINDS: [RegExp, RuleComponentKind][] = [
  [/^Faction_Abilities/, "ability"],
  [/^Faction_Technolog/, "tech"],
  [/^Technology/, "tech"],
  [/^Leaders/, "leader"],
  [/^Faction_Promissory_Note/, "promissory"],
  [/^Breakthrough/, "breakthrough"],
  [/^(Flagship|Mech|War_Sun|Space_Dock|Dreadnought|Carrier|Cruiser|Destroyer|Fighter|Infantry|PDS)/, "unit"],
];

/** Keeps the candidates of the kind listed in the wiki section, when any of them match it. */
function narrowBySection(candidates: Entry[], section: string): Entry[] {
  if (candidates.length < 2 || !section) return candidates;
  const kind = SECTION_KINDS.find(([re]) => re.test(section))?.[1];
  const ofKind = kind ? candidates.filter((c) => c.kind === kind) : [];
  return ofKind.length > 0 ? ofKind : candidates;
}

/** Components with this exact name or, failing that, with this name followed by more words. */
export function findComponentsByName(name: string): RuleComponentRef[] {
  const key = normalizeName(name);
  if (!key) return [];
  const idx = getIndex();
  const exact = idx.get(key);
  if (exact) return exact;
  const extended: Entry[] = [];
  for (const [candidate, entries] of idx) {
    if (candidate.startsWith(`${key} `)) extended.push(...entries);
  }
  return extended;
}

/**
 * Resolves a fandom-wiki link to the in-game components it names, or `[]` when the URL is not
 * a wiki link or names nothing the game knows (the link then stays external).
 */
export function resolveComponentLink(href: string, label: string): RuleComponentRef[] {
  const match = WIKI_URL_RE.exec(href);
  if (!match) return [];
  const page = match[1] ?? "";
  const hash = match[2] ?? "";
  const textAt = hash.indexOf(":~:text=");
  // Without a text fragment the link names a whole page (a faction, an expansion), not one
  // component — it stays a wiki link.
  if (textAt < 0) return [];
  // A text fragment may be a range (`start,end`) — the start is the component name.
  const fragment = safeDecode(hash.slice(textAt + 8).split(",")[0]);
  const section = hash.slice(0, textAt);
  // Labels may carry markdown emphasis (`*Enervate*`); rulings also prefix names with "The"
  // ("The Sorrow") where the game data does not.
  const names = [fragment, label.replace(/[*_]/g, "")].flatMap((n) => [n, n.replace(/^the\s+/i, "")]);
  for (const name of names) {
    const found = findComponentsByName(name) as Entry[];
    if (found.length > 0) {
      return narrowByPage(narrowBySection(found, section), page).map(({ kind, id, name: n }) => ({
        kind,
        id,
        name: n,
      }));
    }
  }
  return [];
}
