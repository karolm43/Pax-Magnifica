import { useState, type CSSProperties } from "react";
import { getPromissoryNoteData } from "@/entities/lookup/promissoryNotes";
import { useFactionColors } from "@/hooks/useFactionColors";
import { PromissoryNoteCard } from "@/domains/cards/components/PromissoryNoteCard";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { getFactionImage } from "@/entities/lookup/factions";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import type { FactionColorMap } from "@/entities/game/types";
import {
  ObjectGlyph,
  ObjectLabel,
  ObjectShell,
} from "@/domains/player/components/silhouettes/ObjectShell";
import { searchKey } from "@/domains/search/searchKeys";
import styles from "./PromissoryNote.module.css";

type Props = {
  promissoryNoteId: string;
  onClick?: () => void;
  showDetails?: boolean;
};

/** The owner's colour as a space-separated RGB triplet for the ticket stub. */
export function getOwnerRgb(
  faction: string,
  color: string | undefined,
  factionColorMap: FactionColorMap,
): string | undefined {
  // Mapa jest kluczowana i frakcją, i kolorem — bierzemy pole `color`, nie klucz
  // (klucz bywa nazwą frakcji, której resolvePrimaryRgb nie zna).
  const ownerColor =
    color ??
    factionColorMap[faction]?.color ??
    Object.values(factionColorMap).find((data) => data.faction === faction)
      ?.color;
  const rgb = ownerColor ? resolvePrimaryRgb(ownerColor) : undefined;
  return rgb ? `${rgb.red}, ${rgb.green}, ${rgb.blue}` : undefined;
}

/**
 * IOU ticket: a stub in the owner's colour carries their mark and tears off
 * along a notched perforation; the sheet keeps its dog-ear. Whose note it is
 * reads before what it says.
 */
export function PromissoryNote({
  promissoryNoteId,
  onClick,
  showDetails = true,
}: Props) {
  const [opened, setOpened] = useState(false);
  const factionColorMap = useFactionColors();
  const promissoryNoteData = getPromissoryNoteData(
    promissoryNoteId,
    factionColorMap,
  );

  if (!promissoryNoteData) return null;

  // Zawsze pełna nazwa karty (decyzja użytkownika) — skróty AsyncTI4 typu
  // "Cybernetic Enh'nc'm'nts" są nieczytelne.
  const { faction, color, displayName: name } = promissoryNoteData;
  const ownerRgb = getOwnerRgb(faction, color, factionColorMap);
  const handleClick = () => {
    if (showDetails) setOpened((o) => !o);
    onClick?.();
  };

  const shell = (
    <ObjectShell
      className={styles.pn}
      label={`${name} · from ${faction}`}
      onClick={handleClick}
      searchKey={searchKey("promissory", promissoryNoteId)}
      style={ownerRgb ? ({ "--pc": ownerRgb } as CSSProperties) : undefined}
    >
      <ObjectGlyph src={getFactionImage(faction)} size={16} />
      <ObjectLabel>{name}</ObjectLabel>
    </ObjectShell>
  );

  if (!showDetails) return shell;

  return (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>{shell}</SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <PromissoryNoteCard promissoryNoteId={promissoryNoteId} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
