/**
 * A rules-content link to an in-game component (faction ability, technology, leader, unit…).
 *
 * Instead of opening the fandom wiki, a click shows the component's in-game card — the same
 * `ComponentCard` the player panel and decision windows show (`UnitDetailsCard` for units).
 * A name that covers several components (e.g. "Valefar Assimilator" = X and Y) shows all of them.
 */

import type { MouseEvent, ReactNode } from "react";
import { ComponentCard } from "@/domains/cards/components/ComponentInfo";
import { UnitDetailsCard } from "@/domains/cards/components/UnitDetailsCard";
import { useDisclosure } from "@/hooks/useDisclosure";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import type { RuleComponentRef } from "@/domains/rules/componentLinks";
import styles from "./ComponentLink.module.css";

function RuleComponentCard({ componentRef }: { componentRef: RuleComponentRef }) {
  const { kind, id } = componentRef;
  if (kind === "unit") return <UnitDetailsCard unitId={id} />;
  return <ComponentCard componentRef={{ kind, id }} />;
}

export function ComponentLink({ refs, children }: { refs: RuleComponentRef[]; children: ReactNode }) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const names = refs.map((r) => r.name).join(", ");
  const onClick = (event: MouseEvent) => {
    event.preventDefault();
    toggle();
  };
  return (
    <SmoothPopover opened={opened} onChange={setOpened} position="bottom">
      <SmoothPopover.Target>
        <button
          type="button"
          className={styles.link}
          aria-label={`Show card: ${names}`}
          aria-expanded={opened}
          onClick={onClick}
        >
          {children}
        </button>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <div className={styles.cards}>
          {refs.map((r) => (
            <RuleComponentCard key={`${r.kind}:${r.id}`} componentRef={r} />
          ))}
        </div>
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
