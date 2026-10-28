import { Image } from "@/ds";
import { SmoothPopover } from "@/shared/ui/SmoothPopover";
import { LeaderDetailsCard } from "@/domains/cards/components/LeaderDetailsCard";
import styles from "./CompactLeader.module.css";
import { useDisclosure } from "@/hooks/useDisclosure";
import { lowPriorityImageProps } from "@/shared/ui/imageLoading";
import { searchKey, searchTarget } from "@/domains/search/searchKeys";
import {
  ContextMenu,
  useContextMenu,
} from "@/shared/ui/ContextMenu/ContextMenu";
import { useBoardEditor } from "@/api/useBoardEditor";
import { getLeaderById } from "@/entities/lookup/leaders";
import { leaderContextMenuItems } from "./leaderMenu";

type Props = {
  id: string;
  exhausted: boolean;
  locked: boolean;
  /** Właściciel (``discordId``) — włącza menu kontekstowe stanu lidera. */
  playerId?: string;
};

export function CompactLeader({ id, exhausted, locked, playerId }: Props) {
  const { opened, setOpened, toggle } = useDisclosure(false);
  const { setLeaderState } = useBoardEditor();
  const ctx = useContextMenu();
  const shouldShowGreen = !exhausted && !locked;
  const menuItems = playerId
    ? leaderContextMenuItems(playerId, id, exhausted, locked, setLeaderState)
    : [];

  return (
    <SmoothPopover opened={opened} onChange={setOpened}>
      <SmoothPopover.Target>
        <div
          className={`${styles.compact} ${shouldShowGreen ? styles.active : styles.inactive}`}
          onClick={toggle}
          onContextMenu={menuItems.length > 0 ? ctx.onContextMenu : undefined}
          role="button"
          tabIndex={0}
          {...searchTarget(searchKey("leader", id))}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              toggle();
            }
          }}
        >
          <div className={styles.imageFrame}>
            <Image
              {...lowPriorityImageProps}
              src={`/leaders/${id}.webp`}
              className={styles.image}
            />
          </div>
        </div>
      </SmoothPopover.Target>
      <SmoothPopover.Dropdown p={0}>
        <LeaderDetailsCard leaderId={id} />
      </SmoothPopover.Dropdown>
      {menuItems.length > 0 && (
        <ContextMenu
          position={ctx.position}
          items={menuItems}
          onClose={ctx.close}
          title={getLeaderById(id)?.name ?? id}
        />
      )}
    </SmoothPopover>
  );
}
