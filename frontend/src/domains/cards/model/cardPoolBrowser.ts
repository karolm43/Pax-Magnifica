import { agendas } from "@/entities/data/agendas";
import { actionCards } from "@/entities/data/actionCards";
import { publicObjectives } from "@/entities/data/publicObjectives";
import { secretObjectives } from "@/entities/data/secretObjectives";
import { relics } from "@/entities/data/relics";
import { explorations } from "@/entities/data/explorations";
import { isOfficialSource } from "@/entities/data/officialSources";

/** Jedna pozycja listy w przeglądarce puli kart. */
export type PoolEntry = {
  alias: string;
  name: string;
  text: string;
  /** Opcjonalna etykieta nad tytułem (np. „Law" / „Directive", „Status phase"). */
  meta?: string;
  /** Liczba fizycznych kopii tej karty w talii (np. 3× „Abandoned Keel"). */
  copies?: number;
  /** Tekst klimatyczny (flavor) z karty — wyświetlany kursywą na dole. */
  flavor?: string;
};

/** Grupa pozycji (np. „Laws", „Directives", „Stage I") z własnym kolorem sygnału. */
export type PoolGroup = {
  title: string;
  tone?: string;
  entries: PoolEntry[];
};

const naturalCollator = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});

function byName(a: PoolEntry, b: PoolEntry): number {
  return naturalCollator.compare(a.name, b.name);
}

/** Łączy teksty agendy (For/Against + efekt mapowy) w jeden blok akapitów. */
function agendaText(text1: string, text2?: string, mapText?: string): string {
  return [text1, text2, mapText]
    .filter((part): part is string => !!part && part.trim().length > 0)
    .join("\n\n");
}

/**
 * Pełna pula agend z aktywnych źródeł, rozbita na Prawa i Dyrektywy.
 * Źródło: statyczne dane `entities/data/agendas` (cała talia, nie stan gry).
 */
export function agendaPool(): PoolGroup[] {
  const official = agendas.filter((a) => isOfficialSource(a.source));
  const laws: PoolEntry[] = [];
  const directives: PoolEntry[] = [];
  for (const a of official) {
    // `target` agendy bywa długim zdaniem (opis elekcji) — idzie do treści jako
    // pierwszy akapit, a krótki `type` zostaje etykietą meta.
    const body = a.target
      ? `${a.target}\n\n${agendaText(a.text1, a.text2, a.mapText)}`
      : agendaText(a.text1, a.text2, a.mapText);
    const entry: PoolEntry = {
      alias: a.alias,
      name: a.name,
      text: body,
      meta: a.type,
    };
    if ((a.type || "").toLowerCase() === "law") laws.push(entry);
    else directives.push(entry);
  }
  laws.sort(byName);
  directives.sort(byName);
  return [
    { title: "Laws", tone: "var(--ds-sig-stage2)", entries: laws },
    { title: "Directives", tone: "var(--ds-sig-stage1)", entries: directives },
  ].filter((group) => group.entries.length > 0);
}

/**
 * Pełna pula kart akcji z aktywnych źródeł (jedna grupa, po nazwie). base, PoK i
 * codexy to ROZŁĄCZNE zestawy prawdziwych kart (codex I dodał nowe karty akcji,
 * np. War Machine/Strategize — NIE są to erraty istniejących). Dlatego bierzemy
 * wszystkie, grupując identyczne kopie po tożsamości karty (`automationID`, albo
 * nazwa+okno) i podając liczbę kopii. Źródło: `entities/data/actionCards`.
 */
export function actionCardPool(): PoolGroup[] {
  const byCard = new Map<string, PoolEntry>();
  for (const c of actionCards) {
    if (!isOfficialSource(c.source)) continue;
    const key = c.automationID || `${c.name}\u0000${c.window}`;
    const existing = byCard.get(key);
    if (existing) {
      existing.copies = (existing.copies ?? 1) + 1;
    } else {
      byCard.set(key, {
        alias: c.alias,
        name: c.name,
        text: c.text,
        meta: c.window,
        copies: 1,
        flavor: c.flavorText,
      });
    }
  }
  const entries = [...byCard.values()].sort(byName);
  return entries.length > 0
    ? [{ title: "Action cards", tone: "var(--ds-sig-war)", entries }]
    : [];
}

/**
 * Pula publicznych celów danego etapu (1 lub 2) z aktywnych źródeł.
 * Etap kodowany jest polem `points` (1 = Etap I, 2 = Etap II).
 * Źródło: statyczne dane `entities/data/publicObjectives`.
 */
export function publicObjectivePool(stage: 1 | 2): PoolGroup[] {
  const tone =
    stage === 1 ? "var(--ds-sig-stage1)" : "var(--ds-sig-stage2)";
  const entries: PoolEntry[] = publicObjectives
    .filter((o) => isOfficialSource(o.source) && o.points === stage)
    .map((o) => ({
      alias: o.alias,
      name: o.name,
      text: o.text,
      meta: `${o.phase} phase`,
    }))
    .sort(byName);
  const title = stage === 1 ? "Stage I" : "Stage II";
  return entries.length > 0 ? [{ title, tone, entries }] : [];
}

/**
 * Pełna pula celów sekretnych z aktywnych źródeł (jedna grupa, po nazwie).
 * To referencja całej talii — nie ręka gracza. Źródło: `entities/data`.
 */
export function secretObjectivePool(): PoolGroup[] {
  const entries: PoolEntry[] = secretObjectives
    .filter((o) => isOfficialSource(o.source))
    .map((o) => ({
      alias: o.alias,
      name: o.name,
      text: o.text,
      meta: `${o.phase} phase`,
    }))
    .sort(byName);
  return entries.length > 0
    ? [{ title: "Secret objectives", tone: "var(--ds-sig-secret)", entries }]
    : [];
}

/**
 * Pełna pula relikwii z aktywnych źródeł (jedna grupa, po nazwie).
 * Źródło: `entities/data/relics`.
 */
export function relicPool(): PoolGroup[] {
  const entries: PoolEntry[] = relics
    .filter((r) => isOfficialSource(r.source))
    .map((r) => ({
      alias: r.alias,
      name: r.name,
      text: r.text,
      flavor: r.flavourText,
    }))
    .sort(byName);
  return entries.length > 0
    ? [{ title: "Relics", tone: "var(--ds-sig-relic)", entries }]
    : [];
}

/** Kolory sygnału cech eksploracji — spójne z ikonami cech na planszy. */
const EXPLORE_TONE: Record<string, string> = {
  Cultural: "var(--ds-sig-prop)",
  Hazardous: "var(--ds-sig-war)",
  Industrial: "var(--ds-sig-bio)",
  Frontier: "var(--ds-sig-pn)",
};

/**
 * Pula kart eksploracji danej cechy z aktywnych źródeł. Talia ma po 20 kart na
 * cechę, ale część to KOPIE tej samej karty (np. 3× „Abandoned Keel"). Nie
 * zwijamy ich do unikatów — grupujemy identyczne karty (nazwa + treść) i
 * podajemy liczbę kopii, więc suma kopii odpowiada rozmiarowi fizycznej talii.
 * Źródło: `entities/data/explorations`.
 */
export function explorationPool(type: string): PoolGroup[] {
  const byCard = new Map<string, PoolEntry>();
  for (const card of explorations) {
    if (!isOfficialSource(card.source)) continue;
    if ((card.type ?? "") !== type) continue;
    const key = `${card.name}\u0000${card.text}`;
    const existing = byCard.get(key);
    if (existing) {
      existing.copies = (existing.copies ?? 1) + 1;
    } else {
      byCard.set(key, {
        alias: card.id,
        name: card.name,
        text: card.text,
        meta: card.resolution,
        copies: 1,
        flavor: card.flavorText,
      });
    }
  }
  const entries = [...byCard.values()].sort(byName);
  return entries.length > 0
    ? [{ title: `${type} exploration`, tone: EXPLORE_TONE[type], entries }]
    : [];
}
