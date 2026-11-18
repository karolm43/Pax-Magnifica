import { promissoryNotes } from "@/entities/data/promissoryNotes";
import { withVariant } from "@/entities/lookup/variantData";
import { indexBy } from "@/entities/lookup/indexBy";
import type { PromissoryNote } from "@/entities/data/types";
import type { FactionColorMap } from "@/entities/game/types";

const promissoryNotesMap = indexBy(
  promissoryNotes.filter((note) => !note.homebrewReplacesID),
  (note) => note.alias
);

/*
 * FAN-AGENDAS: zamienniki oficjalnych notek z wariantu Absol (np. `absol_<color>_ps`,
 * Absol's Political Secret). Backend rozdaje je w grze Absol jako `absol_<kolor>_ps`.
 * Tylko źródło `absol` - inne homebrew zamienniki (np. Black Spectrum) nie są w grze.
 */
const VARIANT_NOTE_SOURCES: ReadonlySet<string> = new Set(["absol"]);
const variantNotesMap = indexBy(
  promissoryNotes.filter(
    (note) => !!note.homebrewReplacesID && VARIANT_NOTE_SOURCES.has(note.source),
  ),
  (note) => note.alias
);

function getPromissoryNoteByAlias(alias: string): PromissoryNote | undefined {
  // Errata modułów wariantów gry (np. Absol's Political Secret pod `<color>_ps`).
  return withVariant("promissory_notes", alias, promissoryNotesMap.get(alias));
}

/**
 * Notka wariantu w formie `<prefiks>_<kolor>_<typ>` (np. `absol_red_ps`) → dane szablonu
 * `absol_<color>_ps` i kolor właściciela; `null`, gdy to nie notka wariantu.
 */
function resolveVariantColorNote(
  promissoryNoteId: string,
): { noteData: PromissoryNote; color: string } | null {
  const parts = promissoryNoteId.split("_");
  if (parts.length < 3) return null;
  const color = parts[1];
  const template = [parts[0], "<color>", ...parts.slice(2)].join("_");
  const noteData = variantNotesMap.get(template);
  return noteData ? { noteData, color } : null;
}

/**
 * Resolves a promissory note ID in either faction-specific ("acq") or
 * color-based ("red_sftt") form to its data and owning faction.
 */
export function getPromissoryNoteData(
  promissoryNoteId: string,
  factionColorMap: FactionColorMap
): {
  noteData: PromissoryNote;
  faction: string;
  color?: string;
  displayName: string;
} | null {
  let noteData = getPromissoryNoteByAlias(promissoryNoteId);

  if (noteData) {
    const faction = noteData.faction;
    if (!faction) {
      console.warn(
        `Faction-specific promissory note "${promissoryNoteId}" has no faction`
      );
      return null;
    }

    return {
      noteData,
      faction,
      displayName: noteData.name,
    };
  }

  const variant = resolveVariantColorNote(promissoryNoteId);
  if (variant) {
    const faction = factionColorMap?.[variant.color]?.faction;
    if (!faction) {
      console.warn(`No faction found for color "${variant.color}"`);
      return null;
    }
    return {
      noteData: variant.noteData,
      faction,
      color: variant.color,
      displayName: variant.noteData.name.replace(/<color>/g, variant.color),
    };
  }

  const parts = promissoryNoteId.split("_");
  if (parts.length < 2) {
    console.warn(`Invalid promissory note ID format: "${promissoryNoteId}"`);
    return null;
  }

  const color = parts[0];
  const type = parts.slice(1).join("_");

  const templateAlias = `<color>_${type}`;
  noteData = getPromissoryNoteByAlias(templateAlias);

  if (!noteData) {
    console.warn(
      `Promissory note template with alias "${templateAlias}" not found`
    );
    return null;
  }

  const faction = factionColorMap?.[color]?.faction;
  if (!faction) {
    console.warn(`No faction found for color "${color}"`);
    return null;
  }

  const displayName = noteData.name.replace(/<color>/g, color);

  return {
    noteData,
    faction,
    color,
    displayName,
  };
}
