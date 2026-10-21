import { UnstyledButton, Stack, Text, Loader, Center } from "@/ds";
import { IconPointFilled } from "@tabler/icons-react";
import { useHistory, useBoardEditor } from "@/api/useBoardEditor";
import styles from "./HistoryPanel.module.css";

/**
 * Tłumaczy techniczną etykietę migawki na czytelny opis po polsku.
 * Zwraca ikonę (emoji) + krótki tytuł; backend emituje etykiety jak
 * ``turn:pass``, ``phase:next``, ``player:p1``, ``edit:301:space`` itd.
 */
function describe(label: string): { icon: string; text: string } {
  const exact: Record<string, { icon: string; text: string }> = {
    initial: { icon: "🎬", text: "Początek gry" },
    "game:new": { icon: "✨", text: "Nowa gra" },
    "move-units": { icon: "➡️", text: "Przeniesienie jednostek" },
    "god-mode-patch": { icon: "🛠️", text: "Korekta God-Mode" },
    replace: { icon: "🛠️", text: "Nadpisanie stanu" },
    "turn:end": { icon: "⏭️", text: "Koniec tury" },
    "turn:pass": { icon: "🏳️", text: "Pas" },
    "phase:next": { icon: "🔄", text: "Następna faza" },
    "round:next": { icon: "🔁", text: "Nowa runda" },
  };
  if (label in exact) return exact[label];

  if (label.startsWith("setup:")) {
    return { icon: "🧩", text: `Setup frakcji · ${label.slice(6)}` };
  }
  if (label.startsWith("player:")) {
    return { icon: "👤", text: `Edycja gracza · ${label.slice(7)}` };
  }
  if (label.startsWith("edit:")) {
    const [, pos, zone] = label.split(":");
    const where = zone === "space" ? "przestrzeń" : zone ? `planeta ${zone}` : "";
    return {
      icon: "✏️",
      text: `Edycja jednostek · ${pos}${where ? ` (${where})` : ""}`,
    };
  }
  if (label.startsWith("space:")) {
    return { icon: "🚀", text: `Jednostki w przestrzeni · ${label.slice(6)}` };
  }
  if (label.startsWith("planet:")) {
    const [, pos, planet] = label.split(":");
    return { icon: "🪐", text: `Jednostki na planecie · ${planet ?? pos}` };
  }
  return { icon: "•", text: label };
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
      {ordered.map((entry) => {
        const { icon, text } = describe(entry.label);
        return (
          <UnstyledButton
            key={entry.seq}
            className={styles.row}
            data-current={entry.is_current || undefined}
            onClick={() => void gotoHistory(entry.seq)}
            title={`Wróć do: ${text}`}
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
