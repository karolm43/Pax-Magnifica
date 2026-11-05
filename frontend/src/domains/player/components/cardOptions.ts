import {
  actionCardPool,
  secretObjectivePool,
} from "@/domains/cards/model/cardPoolBrowser";
import { promissoryNotes as ALL_PROMISSORY_NOTES } from "@/entities/data/promissoryNotes";
import { relics as ALL_RELICS } from "@/entities/data/relics";
import { isOfficialSource } from "@/entities/data/officialSources";

/** Opcja listy wyboru (Select): wartość = id karty/komponentu, etykieta = nazwa. */
export type CardOption = { value: string; label: string };

const naturalCollator = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});

function byLabel(a: CardOption, b: CardOption): number {
  return naturalCollator.compare(a.label, b.label);
}

/** Spłaszcza grupy puli kart do jednej listy opcji ``{value, label}``. */
function fromPool(groups: { entries: { alias: string; name: string }[] }[]): CardOption[] {
  const out: CardOption[] = [];
  const seen = new Set<string>();
  for (const group of groups) {
    for (const entry of group.entries) {
      if (seen.has(entry.alias)) continue;
      seen.add(entry.alias);
      out.push({ value: entry.alias, label: entry.name });
    }
  }
  return out.sort(byLabel);
}

/** Opcje kart akcji (oficjalne źródła), nazwa → alias. */
export function actionCardOptions(): CardOption[] {
  return fromPool(actionCardPool());
}

/** Opcje tajnych celów (oficjalne źródła), nazwa → alias. */
export function secretObjectiveOptions(): CardOption[] {
  return fromPool(secretObjectivePool());
}

/**
 * Opcje promissory notes (oficjalne źródła). Notki szablonowe (``<color>_*``)
 * pomijamy w surowej formie — operator wstawia je przez kolory graczy, a tu
 * pokazujemy frakcyjne i nazwane notki z czytelną nazwą.
 */
export function promissoryNoteOptions(): CardOption[] {
  const out: CardOption[] = [];
  const seen = new Set<string>();
  for (const note of ALL_PROMISSORY_NOTES) {
    if (!isOfficialSource(note.source)) continue;
    if (note.alias.includes("<color>")) continue;
    if (seen.has(note.alias)) continue;
    seen.add(note.alias);
    out.push({ value: note.alias, label: note.name });
  }
  return out.sort(byLabel);
}

/** Opcje relikwii (oficjalne źródła), nazwa → alias. */
export function relicOptions(): CardOption[] {
  const out: CardOption[] = [];
  const seen = new Set<string>();
  for (const relic of ALL_RELICS) {
    if (!isOfficialSource(relic.source)) continue;
    if (seen.has(relic.alias)) continue;
    seen.add(relic.alias);
    out.push({ value: relic.alias, label: relic.name });
  }
  return out.sort(byLabel);
}
