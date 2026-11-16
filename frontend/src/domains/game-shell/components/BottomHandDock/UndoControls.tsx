import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { IconArrowBackUp } from "@tabler/icons-react";
import { postPlayerUndo, usePlayerUndo } from "@/api/useActionCard";
import { useActivityFeed } from "@/api/useBoardEditor";
import { describeActivity } from "@/domains/game-shell/components/ActivityPanel/describeActivity";
import { useActivityContext } from "@/domains/game-shell/components/ActivityPanel/useActivityContext";
import { useAppStore } from "@/state/appStore";
import styles from "./HoldControls.module.css";

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

  const title = available
    ? "Undo your last step"
    : `Undo is not possible: ${data?.reason ?? "nothing of yours to undo"}`;

  return (
    <button
      type="button"
      className={styles.holdBtn}
      disabled={!available || busy}
      aria-disabled={!available || busy}
      title={title}
      onClick={() => void undo()}
    >
      <IconArrowBackUp size={14} aria-hidden="true" />
      <span>Undo</span>
      {available && what && <span className={styles.undoWhat}>{what}</span>}
    </button>
  );
}
