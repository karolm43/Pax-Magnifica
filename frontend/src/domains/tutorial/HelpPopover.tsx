import { useState, type SyntheticEvent } from "react";
import cx from "clsx";
import { ActionIcon, Popover, type PopoverProps } from "@/ds";
import { useTutorialStore } from "@/domains/tutorial/tutorialStore";
import { MICRO_HELPS, type MicroHelp, type MicroHelpId } from "./microHelps";
import styles from "./HelpPopover.module.css";

/** Keeps a click on the help from reaching parents (drag handles, map DragScroll, row clicks). */
const stop = (e: SyntheticEvent) => e.stopPropagation();

/**
 * Contextual micro-help (tutorial Layer 4): a small round `?` that opens a popover with a short
 * explanation and an optional "Learn more" link into the How to play guide. Pointer and mouse
 * events stop at the button, so it never starts a panel drag or a map pan.
 */
export function HelpPopover({
  help,
  position = "bottom",
  className,
}: {
  /** A registered help id (`MICRO_HELPS`) or an inline help. */
  help: MicroHelpId | MicroHelp;
  position?: PopoverProps["position"];
  className?: string;
}) {
  const [opened, setOpened] = useState(false);
  const content: MicroHelp = typeof help === "string" ? MICRO_HELPS[help] : help;
  const chapter = content.chapter;

  return (
    <Popover opened={opened} onChange={setOpened} position={position} offset={6} withArrow>
      <Popover.Target>
        <ActionIcon
          size={18}
          radius="xl"
          variant="subtle"
          className={cx(styles.trigger, className)}
          aria-label={`Help: ${content.topic}`}
          aria-haspopup="dialog"
          aria-expanded={opened}
          data-no-drag
          onPointerDown={stop}
          onMouseDown={stop}
          onDoubleClick={stop}
          onClick={(e: SyntheticEvent) => {
            e.stopPropagation();
            setOpened((o) => !o);
          }}
        >
          ?
        </ActionIcon>
      </Popover.Target>
      <Popover.Dropdown className={styles.panel} onClick={stop} onMouseDown={stop}>
        <div role="dialog" aria-label={content.title} data-no-drag onPointerDown={stop}>
          <h4 className={styles.title}>{content.title}</h4>
          <ul className={styles.lines}>
            {content.lines.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          {chapter && (
            <button
              type="button"
              className={styles.more}
              onClick={() => {
                setOpened(false);
                useTutorialStore.getState().openGuide(chapter);
              }}
            >
              Learn more
            </button>
          )}
        </div>
      </Popover.Dropdown>
    </Popover>
  );
}

export default HelpPopover;
