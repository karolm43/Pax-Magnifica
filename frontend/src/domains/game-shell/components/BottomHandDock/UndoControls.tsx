import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { IconArrowBackUp } from "@tabler/icons-react";
import { Tooltip } from "@/ds";
import { postPlayerUndo, usePlayerUndo } from "@/api/useActionCard";
import { useActivityFeed } from "@/api/useBoardEditor";
import { describeActivity } from "@/domains/game-shell/components/ActivityPanel/describeActivity";
import { useActivityContext } from "@/domains/game-shell/components/ActivityPanel/useActivityContext";
import { useAppStore } from "@/state/appStore";
import styles from "./HoldControls.module.css";
import { ToolHint } from "./ToolHint";

/**
 * Undo gracza (RULES.md 44.7): cofa MÓJ ostatni krok, po jednym. Silnik pozwala tylko, gdy od
 * tamtej chwili nikt inny nie działał, tura nie przeszła dalej, nie było kości / dobrania kart /
 * zmiany fazy / zagrania karty i krok nie dotknął innego gracza. Wyłączony przycisk mówi dlaczego.
 */
export function UndoControls({ playerId }: { playerId: string }) {
  const { data } = usePlayerUndo(playerId);
  const queryClient = useQueryClient();
  const setNotice = useAppStore((s) => s.setNotice);
  const [busy, setBusy] = useState(false);
  // Cofany krok opisany tak samo jak w feedzie Activity (ten sam opis, nie surowa etykieta).
  const { data: feed } = useActivityFeed();
  const ctx = useActivityContext(feed?.players);
  const entry = feed?.entries.find((e) => e.seq === data?.undone_seq);
  const available = data?.available === true;
  const what = entry ? describeActivity(entry.activity, ctx).headline : null;

  const undo = async () => {
    if (busy || !available) return;
    setBusy(true);
    try {
      const error = await postPlayerUndo(playerId);
      if (error) setNotice(error, "error");
      await queryClient.invalidateQueries({ queryKey: ["playerUndo", playerId] });
    } finally {
      setBusy(false);
    }
  };

  const blocked = !available || busy;
  // Opis w dymku (nie w etykiecie): przycisk ma stałą szerokość, pasek ręki się nie rozjeżdża.
  const status = available
    ? what
      ? <>Will undo: {what}</>
      : "Your last step can be undone."
    : `Not possible now: ${data?.reason ?? "nothing of yours to undo"}`;

  return (
    <Tooltip
      position="top"
      multiline
      maw={300}
      label={
        <ToolHint title="Undo" status={status} tone={available ? "info" : "blocked"}>
          Takes back your own last step, one at a time. Only while nobody else has acted since,
          and only before dice, card draws, a played card or a phase change.
        </ToolHint>
      }
    >
      {/* aria-disabled zamiast disabled: wyłączony przycisk też pokazuje dymek z powodem. */}
      <button
        type="button"
        className={styles.toolBtn}
        data-tone="undo"
        aria-disabled={blocked}
        aria-description={
          available
            ? "Take back your last step"
            : `Undo is not possible: ${data?.reason ?? "nothing of yours to undo"}`
        }
        onClick={() => void undo()}
      >
        <IconArrowBackUp size={15} aria-hidden="true" />
        <span className={styles.toolLabel}>Undo</span>
      </button>
    </Tooltip>
  );
}
