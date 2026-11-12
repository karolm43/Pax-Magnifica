import type { KeyboardEvent } from "react";
import { IconLock } from "@tabler/icons-react";
import { useDisclosure } from "@/hooks/useDisclosure";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { LeaderDetailsCard } from "@/domains/cards/components/LeaderDetailsCard";
import { getLeaderById } from "@/entities/lookup/leaders";
import { showLeader } from "@/entities/lookup/showLeader";
import styles from "./Leader.module.css";
import { RankChevrons } from "./RankChevrons";
import { lowPriorityImageProps } from "@/shared/ui/imageLoading";
import { searchKey, searchTarget } from "@/domains/search/searchKeys";
import {
  ContextMenu,
  useContextMenu,
} from "@/shared/ui/ContextMenu/ContextMenu";
import { useBoardEditor } from "@/api/useBoardEditor";
import { leaderContextMenuItems } from "./leaderMenu";
import { IconBolt } from "@tabler/icons-react";
import { useState } from "react";
import { FactionComponentUseModal } from "@/domains/game-shell/components/TurnControls/FactionComponentUseModal";

type Props = {
  id: string;
  type: "agent" | "commander" | "hero";
  exhausted: boolean;
  locked: boolean;
  active: boolean;
  /** Właściciel (``discordId``) — włącza menu kontekstowe stanu lidera. */
  playerId?: string;
  /** Bohater zużyty (RULES.md 61.1). */
  purged?: boolean;
};

function getLeaderState(exhausted: boolean, locked: boolean, purged = false) {
  if (purged) return "exhausted";
  if (locked) return "locked";
  if (exhausted) return "exhausted";
  return undefined;
}

/**
 * Leader dossier row: a squared plate with a cut corner and the portrait in an
 * inset well, and rank chevrons (agent 1, commander 2, hero 3) in the top-right
 * corner. Locked leaders are sockets with a small padlock after their role; exhausted
 * ones are hatched.
 */
export function LeaderChip({
  id,
  type,
  exhausted,
  locked,
  active,
  playerId,
  purged = false,
}: Props) {
  const [using, setUsing] = useState(false);
  const { opened, setOpened, toggle } = useDisclosure(false);
  const { setLeaderState } = useBoardEditor();
  const ctx = useContextMenu();
  const leaderData = getLeaderById(id);
  if (!leaderData) return null;

  const state = getLeaderState(exhausted, locked, purged);
  // Pierwsza pozycja: karta lidera z silnika (użycie ACTION, ręczne odblokowanie) — RULES.md 61.
  const menuItems = playerId
    ? [
        {
          label: "Leader ability…",
          icon: <IconBolt size={14} />,
          onSelect: () => setUsing(true),
        },
        ...leaderContextMenuItems(playerId, id, exhausted, locked, setLeaderState),
      ]
    : [];
  const showPortrait = !locked && showLeader(leaderData.source);
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    toggle();
  };

  return (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>
        <div
          role="button"
          tabIndex={0}
          className={styles.lead}
          data-s={state}
          title={leaderData.name}
          {...searchTarget(searchKey("leader", id))}
          onClick={toggle}
          onContextMenu={menuItems.length > 0 ? ctx.onContextMenu : undefined}
          onKeyDown={handleKeyDown}
        >
          <span className={styles.well}>
            {showPortrait ? (
              <img
                {...lowPriorityImageProps}
                src={`/leaders/${id}.webp`}
                alt=""
              />
            ) : (
              <span aria-hidden="true" />
            )}
          </span>
          <span className={styles.text}>
            <strong>{leaderData.name}</strong>
            <em>
              {type}
              {locked ? (
                <IconLock
                  className={styles.lock}
                  size={11}
                  stroke={2}
                  aria-label="locked"
                />
              ) : purged ? (
                " · purged"
              ) : (
                exhausted && " · exhausted"
              )}
            </em>
          </span>
          <span className={styles.corner}>
            {active && <span className={styles.onlineDot} />}
            <RankChevrons type={type} />
          </span>
        </div>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <LeaderDetailsCard leaderId={id} />
      </SmoothPopover.Dropdown>
      {using && playerId && (
        <FactionComponentUseModal
          kind="leader"
          componentId={id}
          name={leaderData.name}
          playerId={playerId}
          onClose={() => setUsing(false)}
          onDone={() => setUsing(false)}
        />
      )}
      {menuItems.length > 0 && (
        <ContextMenu
          position={ctx.position}
          items={menuItems}
          onClose={ctx.close}
          title={leaderData.name}
        />
      )}
    </SmoothPopover>
  );
}
