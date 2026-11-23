import { useState } from "react";
import { IconCards } from "@tabler/icons-react";
import { getAgenda } from "@/entities/lookup/agendas";
import { ComponentCard } from "@/domains/cards/components/ComponentInfo";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { ObjectLabel, ObjectShell } from "@/domains/player/components/silhouettes/ObjectShell";

type Props = {
  agendaId: string;
  /** Miejsce w talii („Top 1”, „Bottom”) - wiedza gracza o kolejności (RULES.md 53.5.a1). */
  place: string;
};

/**
 * Agenda, którą gracz zna z talii (Insider Information, Politics, M'aban). Ten sam kształt co
 * prawo w strefie gracza (``OwnedLaw``); klik otwiera pełną kartę agendy.
 */
export function KnownAgenda({ agendaId, place }: Props) {
  const [opened, setOpened] = useState(false);
  const name = getAgenda(agendaId)?.name ?? agendaId;
  return (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>
        <ObjectShell label={`${name} · ${place} of the agenda deck`} onClick={() => setOpened((o) => !o)}>
          <IconCards size={16} stroke={1.8} aria-hidden="true" />
          <ObjectLabel>
            {place}: {name}
          </ObjectLabel>
        </ObjectShell>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <ComponentCard componentRef={{ kind: "agenda", id: agendaId }} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
