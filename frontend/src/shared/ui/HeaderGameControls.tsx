import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Group } from "@/ds";
import {
  IconArrowBackUp,
  IconArrowForwardUp,
  IconArrowsExchange,
  IconBook2,
  IconRefresh,
  IconUserEdit,
} from "@tabler/icons-react";
import { useGameDataState } from "@/state/useGameContext";
import { useAppStore } from "@/state/appStore";
import { useBoardEditor } from "@/api/useBoardEditor";
import { PlayerEditorModal } from "@/domains/player/components/PlayerEditorModal";
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
  const navigate = useNavigate();
  const [busy, setBusy] = useState<null | "undo" | "redo">(null);
  const [playerEditorOpen, setPlayerEditorOpen] = useState(false);

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
      <PlayerEditorModal
        opened={playerEditorOpen}
        onClose={() => setPlayerEditorOpen(false)}
      />
      <Button
        variant="default"
        size="xs"
        className={hud.hudButton}
        leftSection={<IconArrowBackUp size={14} />}
        disabled={busy !== null}
        onClick={() => void run("undo")}
        title="Undo"
      >
        Undo
      </Button>
      <Button
        variant="default"
        size="xs"
        className={hud.hudButton}
        leftSection={<IconArrowForwardUp size={14} />}
        disabled={busy !== null}
        onClick={() => void run("redo")}
        title="Redo"
      >
        Redo
      </Button>
      <Button
        variant={moveMode ? "filled" : "default"}
        size="xs"
        className={hud.hudButton}
        leftSection={<IconArrowsExchange size={14} />}
        onClick={toggleMoveMode}
        title="Move mode: click the source system, then the destination"
      >
        {moveMode
          ? moveFrom
            ? "Pick destination…"
            : "Pick source…"
          : "Move"}
      </Button>
      <Button
        variant="default"
        size="xs"
        className={hud.hudButton}
        leftSection={<IconUserEdit size={14} />}
        onClick={() => setPlayerEditorOpen(true)}
        title="God-Mode: edit player data"
      >
        Players
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
        title="Refresh the board"
      >
        Refresh
      </Button>
      {/* Przeglądarka Zasad TI4; `from=game` daje w niej powrót „Wróć do gry". */}
      <Button
        variant="default"
        size="xs"
        className={hud.hudButton}
        leftSection={<IconBook2 size={14} />}
        onClick={() => navigate("/rules?from=game")}
        title="Open the Rules browser"
      >
        Rules
      </Button>
    </Group>
  );
}
