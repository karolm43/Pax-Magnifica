import { useState } from "react";
import { Button, Group } from "@/ds";
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconArrowsExchange,
  IconRefresh,
} from "@tabler/icons-react";
import { useGameDataState } from "@/state/useGameContext";
import { useAppStore } from "@/state/appStore";
import { useBoardEditor } from "@/api/useBoardEditor";
import hud from "./hudChrome.module.css";

/**
 * Sterowanie grą w nagłówku: Cofnij / Ponów (Event Sourcing w backendzie) oraz
 * ręczne odświeżenie planszy (brak live-sync). Wszystko operuje na wspólnym
 * dokumencie web-data i odświeża widok po akcji.
 */
export function HeaderGameControls() {
  const dataState = useGameDataState();
  const { undo, redo } = useBoardEditor();
  const moveMode = useAppStore((s) => s.moveMode);
  const toggleMoveMode = useAppStore((s) => s.toggleMoveMode);
  const moveFrom = useAppStore((s) => s.moveFrom);
  const [busy, setBusy] = useState<null | "undo" | "redo">(null);

  const run = async (which: "undo" | "redo") => {
    if (busy) return;
    setBusy(which);
    try {
      await (which === "undo" ? undo() : redo());
    } finally {
      setBusy(null);
    }
  };

  const loading = dataState?.isLoading ?? false;

  return (
    <Group gap={6} wrap="nowrap" visibleFrom="sm">
      <Button
        variant="default"
        size="xs"
        className={hud.hudButton}
        leftSection={<IconArrowBackUp size={14} />}
        disabled={busy !== null}
        onClick={() => void run("undo")}
        title="Cofnij (Undo)"
      >
        Cofnij
      </Button>
      <Button
        variant="default"
        size="xs"
        className={hud.hudButton}
        leftSection={<IconArrowForwardUp size={14} />}
        disabled={busy !== null}
        onClick={() => void run("redo")}
        title="Ponów (Redo)"
      >
        Ponów
      </Button>
      <Button
        variant={moveMode ? "filled" : "default"}
        size="xs"
        className={hud.hudButton}
        leftSection={<IconArrowsExchange size={14} />}
        onClick={toggleMoveMode}
        title="Tryb przenoszenia: kliknij system źródłowy, potem docelowy"
      >
        {moveMode
          ? moveFrom
            ? "Wybierz cel…"
            : "Wybierz źródło…"
          : "Przenieś"}
      </Button>
      <Button
        variant="default"
        size="xs"
        className={hud.hudButton}
        leftSection={
          <IconRefresh size={14} className={loading ? hud.hudButtonSpin : undefined} />
        }
        disabled={loading}
        onClick={() => dataState?.refetch?.()}
        title="Odśwież planszę"
      >
        Odśwież
      </Button>
    </Group>
  );
}
