import { Button } from "@/ds";
import { formatClock } from "./clockMath";
import { useChessClockView } from "./ChessClockPanel";
import { useClockActions } from "./useClockActions";

/**
 * Sterowanie zegarem W TRWAJĄCEJ grze (Ustawienia → Chess clock, RULES.md 58.1):
 * start z bieżącymi ustawieniami (każdy gracz dostaje pełną pulę od teraz) albo wyłączenie.
 */
export function CurrentGameClockControls({
  gameId,
  minutes,
  incrementSeconds,
}: {
  gameId: string;
  minutes: number;
  incrementSeconds: number;
}) {
  const view = useChessClockView(gameId);
  const actions = useClockActions(gameId);
  const label = view
    ? `Running: ${formatClock(view.initialMs)} per player`
    : "Off in this game";
  return (
    <span style={{ display: "inline-flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
      <span style={{ fontSize: "var(--text-meta)", color: "var(--ds-ink-lo)" }}>{label}</span>
      <Button
        size="xs"
        loading={actions.busy}
        onClick={() => void actions.start(minutes, incrementSeconds)}
      >
        {view ? "Restart clock" : "Start clock"}
      </Button>
      {view && (
        <Button
          size="xs"
          variant="default"
          disabled={actions.busy}
          onClick={() => void actions.disable()}
        >
          Turn off
        </Button>
      )}
    </span>
  );
}
