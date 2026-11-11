import { useEffect, useState, type CSSProperties } from "react";
import cx from "clsx";
import {
  IconGripVertical,
  IconPlayerPauseFilled,
  IconPlayerPlayFilled,
} from "@tabler/icons-react";
import { ActionIcon, Tooltip } from "@/ds";
import { usePlayerData } from "@/api/usePlayerData";
import { useDraggablePanel } from "@/hooks/useDraggablePanel";
import { resolvePrimaryRgb } from "@/entities/lookup/colors";
import type { ChessClockView, PlayerDataResponse } from "@/entities/data/types";
import { formatClock, formatElapsed, isLow, isTicking, livePlayer } from "./clockMath";
import { useClockActions } from "./useClockActions";
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

/** Zegar gry z web-data (`chessClock`) — null, gdy gra jest bez zegara. */
export function useChessClockView(gameId: string) {
  return usePlayerData(gameId, {
    select: (data: PlayerDataResponse) => data.chessClock ?? null,
  }).data;
}

/**
 * Zegar szachowy graczy (RULES.md 58): pasek w widoku mapy z pozostałym czasem każdego
 * gracza i czasem bieżącej tury tego, kto teraz decyduje. Liczy silnik; UI tylko dolicza
 * upływ między odświeżeniami. Nie renderuje się, gdy gra jest bez zegara (włączenie:
 * Ustawienia → Chess clock). Przesuwalny za uchwyt (dwuklik = powrót na miejsce).
 */
export function ChessClockPanel({ gameId }: { gameId: string }) {
  const view = useChessClockView(gameId);
  const actions = useClockActions(gameId);
  const drag = useDraggablePanel("chessClock.pos");
  const [now, setNow] = useState(() => Date.now());
  const ticking = isTicking(view);

  useEffect(() => {
    if (!ticking) return;
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, [ticking]);

  if (!view) return null;
  const delta = ticking ? Math.max(0, now - receiptTime(view)) : 0;
  // Po przeciągnięciu hook ustawia left/top — wyłączamy wtedy centrowanie transformem.
  const style: CSSProperties =
    "left" in drag.style ? { ...drag.style, transform: "none" } : drag.style;

  return (
    <div
      className={styles.bar}
      style={style}
      data-draggable-panel
      data-dragging={drag.isDragging || undefined}
      data-testid="chess-clock"
      role="group"
      aria-label="Player clocks"
    >
      <span
        className={styles.grip}
        onPointerDown={drag.onHandlePointerDown}
        onDoubleClick={drag.reset}
        title="Drag to move (double-click to reset)"
        aria-hidden
      >
        <IconGripVertical size={14} />
      </span>
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
          data-no-drag
          aria-label={view.paused ? "Resume clocks" : "Pause clocks"}
          disabled={actions.busy}
          onClick={() => void (view.paused ? actions.resume() : actions.pause())}
        >
          {view.paused ? <IconPlayerPlayFilled size={14} /> : <IconPlayerPauseFilled size={14} />}
        </ActionIcon>
      </Tooltip>
    </div>
  );
}
