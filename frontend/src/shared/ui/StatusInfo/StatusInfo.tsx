import { useState, type KeyboardEvent, type ReactNode } from "react";
import { DetailsCard } from "@/shared/ui/DetailsCard";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import styles from "./StatusInfo.module.css";

/** Opisy statusów gracza (źródło: docs/rules_tirules - R_speaker, R_action_phase, R_initiative_order). */
export const STATUS_INFO = {
  active: {
    name: "Active",
    text: "It is this player's turn. They perform one action now (tactical, strategic, component or pass); the turn then moves on in initiative order.",
  },
  passed: {
    name: "Passed",
    text: "This player passed in the action phase: they take no more turns and perform no more actions this phase. They can still resolve secondary abilities of other players' strategy cards and play non-component action cards.",
  },
  speaker: {
    name: "Speaker",
    text: "Holds the speaker token. Chooses a strategy card first in the strategy phase, reveals the agenda before each vote, votes last and breaks ties, and reveals the public objective in the status phase. The Politics primary can pass the token to another player.",
  },
  tyrant: {
    name: "Tyrant",
    text: "Marks the player who holds the Tyrant role. It is a title only: it has no effect on turn order or voting in this game.",
  },
  initiativeZero: {
    name: "Naalu \"0\" token",
    text: "The Naalu player's token lies on their strategy card, so their initiative is 0 instead of the number printed on the card. They go first in the strategy card initiative order each round.",
  },
} as const;

export type StatusKey = keyof typeof STATUS_INFO;

/**
 * Status gracza (Passed, Speaker, token „0” Naalu…): bez podpowiedzi po najechaniu -
 * klik otwiera kartę z nazwą statusu i wyjaśnieniem, co on oznacza (decyzja użytkownika).
 */
export function StatusInfo({ status, children }: { status: StatusKey; children: ReactNode }) {
  const [opened, setOpened] = useState(false);
  const info = STATUS_INFO[status];
  const toggle = () => setOpened((o) => !o);
  const onKeyDown = (event: KeyboardEvent<HTMLSpanElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    toggle();
  };
  return (
    <SmoothPopover opened={opened} onChange={setOpened} position="bottom">
      <SmoothPopover.Target>
        <span
          className={styles.target}
          role="button"
          tabIndex={0}
          aria-haspopup="dialog"
          aria-expanded={opened}
          aria-label={`${info.name} - what is this?`}
          onClick={(event) => {
            event.stopPropagation();
            toggle();
          }}
          onKeyDown={onKeyDown}
        >
          {children}
        </span>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <DetailsCard width={300}>
          <DetailsCard.Title title={info.name} type="Status" />
          <DetailsCard.Section title="What it means" content={info.text} />
        </DetailsCard>
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}
