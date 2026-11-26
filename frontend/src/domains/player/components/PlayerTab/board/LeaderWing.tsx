import type { KeyboardEvent } from "react";
import { IconLock } from "@tabler/icons-react";
import { useDisclosure } from "@/hooks/useDisclosure";
import { useIsTwilightsFallMode } from "@/hooks/useIsTwilightsFallMode";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { lowPriorityImageProps } from "@/shared/ui/imageLoading";
import { LeaderDetailsCard } from "@/domains/cards/components/LeaderDetailsCard";
import { searchKey, searchTarget } from "@/domains/search/searchKeys";
import { getLeaderById } from "@/entities/lookup/leaders";
import { showLeader } from "@/entities/lookup/showLeader";
import type { Leader, PlayerData } from "@/entities/data/types";
import { SheetUnit } from "./SheetUnit";
import styles from "./LeaderWing.module.css";

/*
 * Left wing of the player zone: the organizer with one recessed slot per card - AGENT,
 * COMMANDER, HERO, MECH. Leader state is live; click opens the same card as the leader chips.
 */

const SLOTS = ["agent", "commander", "hero"] as const;

type LeaderState = "locked" | "ready" | "exhausted" | "purged";

const STATE_LABEL: Record<LeaderState, string> = {
  locked: "Locked",
  ready: "Ready",
  exhausted: "Exhausted",
  purged: "Purged",
};

function leaderState(leader: Leader): LeaderState {
  if (leader.purged) return "purged";
  if (leader.locked) return "locked";
  return leader.exhausted ? "exhausted" : "ready";
}

function LeaderSlotCard({ leader }: { leader: Leader }) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const twilightsFall = useIsTwilightsFallMode();
  const data = getLeaderById(leader.id);
  if (!data) return null;

  const state = leaderState(leader);
  const name = (twilightsFall && data.tfName) || data.name;
  const text = (twilightsFall && data.tfAbilityText) || data.abilityText;
  const window = (twilightsFall && data.tfAbilityWindow) || data.abilityWindow;
  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    toggle();
  };

  return (
    <SmoothPopover opened={opened} onChange={setOpened} position="right">
      <SmoothPopover.Target>
        <div
          role="button"
          tabIndex={0}
          className={styles.card}
          data-state={state}
          aria-label={`${name}, ${data.type}, ${STATE_LABEL[state].toLowerCase()}`}
          aria-expanded={opened}
          {...searchTarget(searchKey("leader", leader.id))}
          onClick={toggle}
          onKeyDown={onKeyDown}
        >
          {showLeader(data.source) && (
            <img
              {...lowPriorityImageProps}
              className={styles.portrait}
              src={`/leaders/${leader.id}.webp`}
              alt=""
            />
          )}
          <div className={styles.text}>
            <strong>{name}</strong>
            <span className={styles.state}>
              {state === "locked" && <IconLock size={10} aria-hidden="true" />}
              {STATE_LABEL[state]}
              {leader.alliance && " · alliance"}
              {leader.tgCount > 0 && ` · ${leader.tgCount} TG`}
            </span>
            {state === "locked" ? (
              <p>
                <b>Unlock:</b> {data.unlockCondition}
              </p>
            ) : (
              <p>
                <b>{window}</b> {text}
              </p>
            )}
          </div>
        </div>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <LeaderDetailsCard leaderId={leader.id} />
      </SmoothPopover.Dropdown>
    </SmoothPopover>
  );
}

export function LeaderWing({ player }: { player: PlayerData }) {
  const leaders = player.leaders ?? [];
  const others = leaders.filter((l) => !(SLOTS as readonly string[]).includes(l.type));
  const slots: { label: string; cards: Leader[] }[] = [
    ...SLOTS.map((type) => ({ label: type, cards: leaders.filter((l) => l.type === type) })),
    // Anything else the data reports still gets its own slot.
    ...others.map((leader) => ({ label: leader.type, cards: [leader] })),
  ];

  return (
    <section className={styles.wing} aria-label="Leaders and mech">
      {slots.map(({ label, cards }) => (
        <div key={label} className={styles.slot} role="group" aria-label={label}>
          <span className={styles.tab} aria-hidden="true">
            {label}
          </span>
          <div className={styles.well}>
            {cards.length === 0 ? (
              <span className={styles.empty}>Empty</span>
            ) : (
              cards.map((leader, i) => <LeaderSlotCard key={`${leader.id}-${i}`} leader={leader} />)
            )}
          </div>
        </div>
      ))}
      <div className={styles.slot} role="group" aria-label="mech">
        <span className={styles.tab} aria-hidden="true">
          mech
        </span>
        <div className={styles.well}>
          <SheetUnit asyncId="mf" player={player} variant="mech" />
        </div>
      </div>
    </section>
  );
}
