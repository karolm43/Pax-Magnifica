import { UnstyledButton, Stack, Text, Loader, Center } from "@/ds";
import { IconPointFilled } from "@tabler/icons-react";
import { useHistory, useBoardEditor } from "@/api/useBoardEditor";
import styles from "./HistoryPanel.module.css";

/** Tłumaczy techniczną etykietę migawki na czytelny opis po polsku. */
function describe(label: string): string {
  if (label === "initial") return "Początek";
  if (label === "game:new") return "Nowa gra";
  if (label === "move-units") return "Przeniesienie jednostek";
  if (label === "god-mode-patch") return "Korekta God-Mode";
  if (label === "replace") return "Nadpisanie stanu";
  if (label.startsWith("setup:")) return `Setup frakcji: ${label.slice(6)}`;
  if (label.startsWith("edit:")) {
    const [, pos, zone] = label.split(":");
    return `Edycja jednostek · ${pos}${zone ? ` (${zone})` : ""}`;
  }
  if (label.startsWith("space:")) return `Jednostki w przestrzeni · ${label.slice(6)}`;
  if (label.startsWith("planet:")) return `Jednostki na planecie · ${label.slice(7)}`;
  return label;
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
        Nie udało się pobrać historii.
      </Text>
    );
  }

  // Najnowsze na górze.
  const ordered = [...entries].reverse();

  return (
    <Stack gap={2} className={styles.list}>
      {ordered.map((entry) => (
        <UnstyledButton
          key={entry.seq}
          className={styles.row}
          data-current={entry.is_current || undefined}
          onClick={() => void gotoHistory(entry.seq)}
          title={`Wróć do: ${describe(entry.label)}`}
        >
          <span className={styles.dot}>
            {entry.is_current && <IconPointFilled size={12} />}
          </span>
          <span className={styles.label}>{describe(entry.label)}</span>
          <span className={styles.seq}>#{entry.seq}</span>
        </UnstyledButton>
      ))}
    </Stack>
  );
}
