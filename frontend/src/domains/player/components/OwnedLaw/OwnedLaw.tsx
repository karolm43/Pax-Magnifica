import { useState } from "react";
import { IconScale } from "@tabler/icons-react";
import { useGameData } from "@/state/useGameContext";
import { getAgenda } from "@/entities/lookup/agendas";
import { LawDetailsCard } from "@/domains/cards/components/LawDetailsCard";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { ObjectLabel, ObjectShell } from "@/domains/player/components/silhouettes/ObjectShell";
import { searchKey } from "@/domains/search/searchKeys";

type Props = { lawId: string };

/**
 * Prawo w strefie gracza (wygrał wybory „Elect Player" na agendzie). Klik otwiera pełną
 * kartę prawa - tę samą co w panelu „Laws in play".
 */
export function OwnedLaw({ lawId }: Props) {
  const [opened, setOpened] = useState(false);
  const law = useGameData()?.lawsInPlay?.find((l) => l.id === lawId);
  const name = law?.name ?? getAgenda(lawId)?.name ?? lawId;

  const shell = (
    <ObjectShell
      label={`${name} · law`}
      onClick={() => setOpened((o) => !o)}
      searchKey={searchKey("law", lawId)}
    >
      <IconScale size={16} stroke={1.8} aria-hidden="true" />
      <ObjectLabel>{name}</ObjectLabel>
    </ObjectShell>
  );

  if (!law) return shell;
  return (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>{shell}</SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <LawDetailsCard law={law} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
