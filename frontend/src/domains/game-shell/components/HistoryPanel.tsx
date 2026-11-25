import { type ReactNode } from "react";
import { UnstyledButton, Stack, Text, Loader, Center } from "@/ds";
import {
  IconArrowRight,
  IconFlag,
  IconPencil,
  IconPlanet,
  IconPlayerPlay,
  IconPlayerTrackNext,
  IconPointFilled,
  IconPuzzle,
  IconRefresh,
  IconRepeat,
  IconRocket,
  IconSparkles,
  IconTool,
  IconUser,
} from "@tabler/icons-react";
import { useHistory, useBoardEditor } from "@/api/useBoardEditor";
import styles from "./HistoryPanel.module.css";

const ICON_SIZE = 13;

/**
 * Translates a technical snapshot label into a readable label and Tabler icon.
 */
function describe(label: string): { icon: ReactNode; text: string } {
  const exact: Record<string, { icon: ReactNode; text: string }> = {
    initial: { icon: <IconPlayerPlay size={ICON_SIZE} />, text: "Game start" },
    "game:new": { icon: <IconSparkles size={ICON_SIZE} />, text: "New game" },
    "move-units": { icon: <IconArrowRight size={ICON_SIZE} />, text: "Units moved" },
    "god-mode-patch": { icon: <IconTool size={ICON_SIZE} />, text: "God-Mode correction" },
    replace: { icon: <IconTool size={ICON_SIZE} />, text: "State overwritten" },
    "turn:end": { icon: <IconPlayerTrackNext size={ICON_SIZE} />, text: "End of turn" },
    "turn:pass": { icon: <IconFlag size={ICON_SIZE} />, text: "Pass" },
    "phase:next": { icon: <IconRefresh size={ICON_SIZE} />, text: "Next phase" },
    "round:next": { icon: <IconRepeat size={ICON_SIZE} />, text: "New round" },
  };
  if (label in exact) return exact[label];

  if (label.startsWith("setup:")) {
    return { icon: <IconPuzzle size={ICON_SIZE} />, text: `Faction setup · ${label.slice(6)}` };
  }
  if (label.startsWith("player:")) {
    return { icon: <IconUser size={ICON_SIZE} />, text: `Player edit · ${label.slice(7)}` };
  }
  if (label.startsWith("edit:")) {
    const [, pos, zone] = label.split(":");
    const where = zone === "space" ? "space" : zone ? `planet ${zone}` : "";
    return {
      icon: <IconPencil size={ICON_SIZE} />,
      text: `Unit edit · ${pos}${where ? ` (${where})` : ""}`,
    };
  }
  if (label.startsWith("space:")) {
    return { icon: <IconRocket size={ICON_SIZE} />, text: `Units in space · ${label.slice(6)}` };
  }
  if (label.startsWith("planet:")) {
    const [, pos, planet] = label.split(":");
    return { icon: <IconPlanet size={ICON_SIZE} />, text: `Units on planet · ${planet ?? pos}` };
  }
  return { icon: <IconPointFilled size={10} />, text: label };
}

/**
 * Panel historii (Event Sourcing). Pokazuje wszystkie migawki stanu z backendu
 * i pozwala wrócić do dowolnego punktu (undo/redo do punktu) jednym kliknięciem.
 */
export function HistoryPanel() {
  const { data: entries, isLoading, isError } = useHistory();
  const { gotoHistory } = useBoardEditor();

  if (isLoading) {
    return (
      <Center className={styles.state}>
        <Loader size="sm" />
      </Center>
    );
  }
  if (isError || !entries) {
    return (
      <Text size="sm" c="dimmed" className={styles.state}>
        Failed to load history.
      </Text>
    );
  }

  // Najnowsze na górze.
  const ordered = [...entries].reverse();

  return (
    <Stack gap={2} className={styles.list}>
      {ordered.map((entry) => {
        const { icon, text } = describe(entry.label);
        return (
          <UnstyledButton
            key={entry.seq}
            className={styles.row}
            data-current={entry.is_current || undefined}
            onClick={() => void gotoHistory(entry.seq)}
            title={`Go back to: ${text}`}
          >
            <span className={styles.dot}>
              {entry.is_current ? (
                <IconPointFilled size={12} />
              ) : (
                <span className={styles.icon}>{icon}</span>
              )}
            </span>
            <span className={styles.label}>{text}</span>
            <span className={styles.seq}>#{entry.seq}</span>
          </UnstyledButton>
        );
      })}
    </Stack>
  );
}
