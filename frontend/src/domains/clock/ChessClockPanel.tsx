import { useEffect, useState, type CSSProperties } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import cx from "clsx";
import { IconPlayerPauseFilled, IconPlayerPlayFilled } from "@tabler/icons-react";
import { ActionIcon, Tooltip } from "@/ds";
import { DEFAULT_GAME_ID } from "@/config";
import { usePlayerData } from "@/api/usePlayerData";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import { useAppStore } from "@/state/appStore";
import type { ChessClockView, PlayerDataResponse } from "@/entities/data/types";
import { formatClock, formatElapsed, isLow, isTicking, livePlayer } from "./clockMath";
import styles from "./ChessClockPanel.module.css";

// Chwila ODBIORU każdego dokumentu zegara (obiekt z react-query zmienia się przy każdym
// nowym web-data). Liczymy upływ od niej, a nie od czasu serwera — dzięki temu różnica
// zegarów komputerów graczy w grze sieciowej nie ma znaczenia.
const receivedAt = new WeakMap<ChessClockView, number>();
function receiptTime(view: ChessClockView): number {
  let at = receivedAt.get(view);
  if (at === undefined) {
    at = Date.now();
    receivedAt.set(view, at);
  }
  return at;
}

async function postClock(action: "pause" | "resume"): Promise<void> {
  const response = await fetch(`/bot/clock/${action}`, { method: "POST" });
  if (!response.ok) {
    const raw = await response.text().catch(() => "");
    let message = raw || `Error ${response.status}`;
    try {
      const parsed = JSON.parse(raw) as { detail?: unknown };
      if (typeof parsed.detail === "string") message = parsed.detail;
    } catch {
      // nie-JSON - zostaje surowy tekst
    }
    useAppStore.getState().setNotice(message, "error");
  }
}

/**
 * Zegar szachowy graczy (RULES.md 58): pasek nad mapą z pozostałym czasem każdego gracza
 * i czasem bieżącej tury tego, kto teraz decyduje. Liczy silnik; UI tylko dolicza upływ
 * między odświeżeniami. Nie renderuje się, gdy gra jest bez zegara. Montowany raz na stronie gry.
 */
export function ChessClockPanel() {
  const params = useParams<{ mapid: string }>();
  const gameId = params.mapid ?? DEFAULT_GAME_ID;
  const { data: view } = usePlayerData(gameId, {
    select: (data: PlayerDataResponse) => data.chessClock ?? null,
  });
  const queryClient = useQueryClient();
  const [now, setNow] = useState(() => Date.now());
  const [busy, setBusy] = useState(false);
  const ticking = isTicking(view);

  useEffect(() => {
    if (!ticking) return;
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, [ticking]);

  if (!view) return null;
  const delta = ticking ? Math.max(0, now - receiptTime(view)) : 0;

  const togglePause = async () => {
    setBusy(true);
    try {
      await postClock(view.paused ? "resume" : "pause");
      await queryClient.invalidateQueries({ queryKey: ["playerData", gameId] });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.bar} data-testid="chess-clock" role="group" aria-label="Player clocks">
      {view.players.map((raw) => {
        const player = livePlayer(raw, delta);
        const holder = player.playerId === view.holderId;
        const rgb = player.color ? resolvePrimaryRgb(player.color) : undefined;
        const over = player.remainingMs < 0;
        return (
          <div
            key={player.playerId}
            className={cx(styles.player, {
              [styles.holder]: holder,
              [styles.low]: !over && isLow(player, view.initialMs),
              [styles.over]: over,
            })}
            style={
              rgb
                ? ({ "--clock-rgb": `${rgb.red} ${rgb.green} ${rgb.blue}` } as CSSProperties)
                : undefined
            }
          >
            <span className={styles.name} title={player.name}>
              {player.name}
            </span>
            <span className={styles.remaining} aria-label={`${player.name} time left`}>
              {formatClock(player.remainingMs)}
            </span>
            {holder && (
              <span className={styles.turn} aria-label="Current turn time">
                {view.paused ? "paused" : `turn ${formatElapsed(player.turnMs)}`}
              </span>
            )}
          </div>
        );
      })}
      <Tooltip label={view.paused ? "Resume clocks" : "Pause clocks"}>
        <ActionIcon
          variant="subtle"
          size="sm"
          aria-label={view.paused ? "Resume clocks" : "Pause clocks"}
          disabled={busy}
          onClick={() => void togglePause()}
        >
          {view.paused ? <IconPlayerPlayFilled size={14} /> : <IconPlayerPauseFilled size={14} />}
        </ActionIcon>
      </Tooltip>
    </div>
  );
}
