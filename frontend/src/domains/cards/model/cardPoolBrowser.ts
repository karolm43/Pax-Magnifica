import { agendas } from "@/entities/data/agendas";
import { actionCards } from "@/entities/data/actionCards";
import { publicObjectives } from "@/entities/data/publicObjectives";
import { isOfficialSource } from "@/entities/data/officialSources";

/** Jedna pozycja listy w przeglądarce puli kart (bez liczności egzemplarzy). */
export type PoolEntry = {
  alias: string;
  name: string;
  text: string;
  /** Opcjonalna etykieta nad tytułem (np. „Law" / „Directive", „Status phase"). */
  meta?: string;
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
    const entry: PoolEntry = {
      alias: a.alias,
      name: a.name,
      text: agendaText(a.text1, a.text2, a.mapText),
      meta: a.target || a.type,
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
 * Pełna pula kart akcji z aktywnych źródeł (jedna grupa, sortowana po nazwie).
 * Źródło: statyczne dane `entities/data/actionCards`.
 */
export function actionCardPool(): PoolGroup[] {
  const entries: PoolEntry[] = actionCards
    .filter((c) => isOfficialSource(c.source))
    .map((c) => ({
      alias: c.alias,
      name: c.name,
      text: c.text,
      meta: c.window,
    }))
    .sort(byName);
  return entries.length > 0 ? [{ title: "Action cards", entries }] : [];
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
